"""tello_single_socket_with_video.py
Управление одним‑или‑несколькими DJI Tello через общий UDP‑сокет + вывод видеопотока
без изменения общей структуры (одна точка входа `control_drone`, один сокет 9000).

* для каждого дрона: send_command → retries → takeoff → управление
* после `streamon` создаётся поток `video_display()` на OpenCV
* окно можно закрыть клавишей **q** или при посадке

При необходимости отключить видео — поставьте `VIDEO_ENABLED = False`.
"""

import socket
import threading
import time
import keyboard
import asyncio
import cv2
import SearchIPAsync

# ----- Глобальные переменные -----
console_lock = threading.Lock()
socket_udp = None   # общий UDP‑сокет (биндимся в main)

# ----- Настройки -----
MOVE_DIST = 50      # см за одну команду перемещения
TURN_ANGLE = 60     # градусов за одну команду поворота
MIN_BATTERY = 40    # минимальный заряд для взлёта (%)
VIDEO_ENABLED = True


# ===== Служебные функции =====

def send_command(command: str, addr: tuple[str, int], timeout: float = 5):
    """Отправить команду и вернуть ответ как str или None (при ошибке)."""
    try:
        socket_udp.settimeout(timeout)
        socket_udp.sendto(command.encode("utf-8"), addr)
        response, _ = socket_udp.recvfrom(1024)
        return response.decode("utf-8")
    except Exception as e:
        with console_lock:
            print(f"[{addr[0]}] Ошибка '{command}': {e}")
        return None


def send_with_retry(command: str, addr: tuple[str, int], retries: int = 3, delay: float = 1):
    """Отправляет команду до получения 'ok' или пока не кончатся попытки."""
    for attempt in range(1, retries + 1):
        resp = send_command(command, addr)
        if resp == "ok":
            with console_lock:
                print(f"[{addr[0]}] '{command}' — ok")
            return True
        with console_lock:
            print(f"[{addr[0]}] Попытка {attempt}: '{command}' → '{resp}'")
        time.sleep(delay)
    with console_lock:
        print(f"[{addr[0]}] Команда '{command}' провалена после {retries} попыток")
    return False


def battery_check(addr: tuple[str, int], retries: int = 3):
    """Считывает уровень батареи; True, если >= MIN_BATTERY."""
    for _ in range(retries):
        resp = send_command("battery?", addr)
        try:
            level = int(resp)
            with console_lock:
                print(f"[{addr[0]}] Battery: {level}%")
            return level >= MIN_BATTERY
        except (TypeError, ValueError):
            with console_lock:
                print(f"[{addr[0]}] Ответ на battery? непонятен: '{resp}', повтор…")
            time.sleep(1)
    return False


# ===== Видео =====

def video_display(stop_evt: threading.Event, window_name: str):
    """Показывает поток с порта 11111, пока не сработает stop_evt."""
    cap = cv2.VideoCapture("udp://@0.0.0.0:11111")
    if not cap.isOpened():
        with console_lock:
            print("[VIDEO] Не удалось открыть видеопоток (port 11111)")
        return

    while not stop_evt.is_set():
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow(window_name, frame)
        # Закрыть окно вручную — клавиша 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            stop_evt.set()
            break

    cap.release()
    cv2.destroyWindow(window_name)


# ===== Управление дроном =====

def control_drone(ip: str, port: int = 8889):
    addr = (ip, port)

    with console_lock:
        print(f"[{ip}] Включаем SDK…")
    if not send_with_retry("command", addr):
        return

    if not battery_check(addr):
        return

    # Видеопоток: включаем до взлёта, даём дрону время начать стримить
    stop_video_evt = threading.Event()
    if VIDEO_ENABLED:
        send_with_retry("streamon", addr)
        video_thr = threading.Thread(target=video_display, args=(stop_video_evt, f"Tello {ip}"), daemon=True)
        video_thr.start()
        # Короткая пауза, чтобы поток пошёл
        time.sleep(0.5)

    # Взлёт
    if not send_with_retry("takeoff", addr, retries=5, delay=2):
        if VIDEO_ENABLED:
            send_with_retry("streamoff", addr)
            stop_video_evt.set()
        return

    send_with_retry(f"up {MOVE_DIST}", addr)

    with console_lock:
        print(f"[{ip}] Управление: WASD/стрелки Q/E — повороты, Space — флип, L — посадка")

    try:
        while True:
            if keyboard.is_pressed("w"):
                send_with_retry(f"forward {MOVE_DIST}", addr)
            elif keyboard.is_pressed("s"):
                send_with_retry(f"back {MOVE_DIST}", addr)
            elif keyboard.is_pressed("a"):
                send_with_retry(f"left {MOVE_DIST}", addr)
            elif keyboard.is_pressed("d"):
                send_with_retry(f"right {MOVE_DIST}", addr)
            elif keyboard.is_pressed("up"):
                send_with_retry(f"up {MOVE_DIST}", addr)
            elif keyboard.is_pressed("down"):
                send_with_retry(f"down {MOVE_DIST}", addr)
            elif keyboard.is_pressed("q"):
                send_with_retry(f"ccw {TURN_ANGLE}", addr)
            elif keyboard.is_pressed("e"):
                send_with_retry(f"cw {TURN_ANGLE}", addr)
            elif keyboard.is_pressed("space"):
                send_with_retry("flip f", addr)
            elif keyboard.is_pressed("l"):
                send_with_retry("land", addr)
                with console_lock:
                    print(f"[{ip}] Посадка выполнена")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        send_with_retry("land", addr)
        with console_lock:
            print(f"[{ip}] Аварийная посадка (Ctrl+C)")
    finally:
        if VIDEO_ENABLED:
            send_with_retry("streamoff", addr)
            stop_video_evt.set()
            video_thr.join(timeout=2)


# ===== Точка входа =====

def main():
    global socket_udp

    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind(("", 9000))  # общий порт, как и раньше

    num = int(input("Сколько дронов подключить? → "))
    ips = asyncio.run(SearchIPAsync.find_connected_drones(num)) or []
    if not ips:
        print("Дроны не найдены.")
        return

    with console_lock:
        print("Найденные IP:", ips)

    threads = [threading.Thread(target=control_drone, args=(ip,)) for ip in ips]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    socket_udp.close()


if __name__ == "__main__":
    main()

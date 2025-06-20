"""tello_multi_sync_lock.py
Управление группой DJI Tello через **один** UDP-сокет (порт 9000) с:

• безопасной синхронизацией высоты после взлёта;
• глобальной блокировкой `socket_lock`, чтобы ответы разных дронов
  не путались в общем сокете.

Клавиши управления (для каждого активного потока):
    WASD  / ←→↑↓   — перемещение на MOVE_DIST (см)
    Q / E          — поворот на TURN_ANGLE (°)
    Space          — flip f (если батарея ≥ 60 %)
    L              — посадка
"""

import socket
import threading
import time
import keyboard
import asyncio
import SearchIPAsync

# ── настройки ──────────────────────────────────────────────────────────
MOVE_DIST   = 50      # см за один шаг
TURN_ANGLE  = 60      # градусов за один поворот
MIN_BATTERY = 40      # % для разрешения взлёта
ALT_TOLER   = 10      # допуск при выравнивании (см)

# ── глобальные объекты ─────────────────────────────────────────────────
console_lock = threading.Lock()      # красиво печатаем из разных потоков
socket_lock  = threading.Lock()      # атомарная работа с socket_udp
socket_udp   = None                  # общий UDP-сокет (создаётся в main)

heights      = {}                    # реальные высоты дронов {ip: cm}
heights_lock = threading.Lock()
barrier      = None                  # будет создан в main()


# ── низкоуровневые функции ─────────────────────────────────────────────
def send_command(cmd: str, addr: tuple[str, int], timeout: float = 5) -> str | None:
    """Отправить команду и вернуть ответ (str) или None при тайм-ауте."""
    with socket_lock:
        socket_udp.settimeout(timeout)
        try:
            socket_udp.sendto(cmd.encode("utf-8"), addr)
            resp, _ = socket_udp.recvfrom(1024)
            return resp.decode("utf-8").strip()
        except socket.timeout:
            return None
        except Exception as e:
            with console_lock:
                print(f"[{addr[0]}] Ошибка '{cmd}': {e}")
            return None


def send_with_retry(cmd: str, addr: tuple[str, int],
                    retries: int = 3, delay: float = 1) -> bool:
    """Повторяем команду, пока не придёт 'ok' или не исчерпаем попытки."""
    for attempt in range(1, retries + 1):
        resp = send_command(cmd, addr)
        if resp == "ok":
            with console_lock:
                print(f"[{addr[0]}] '{cmd}' — ok")
            return True
        with console_lock:
            print(f"[{addr[0]}] Попытка {attempt}: '{cmd}' → '{resp}'")
        time.sleep(delay)
    with console_lock:
        print(f"[{addr[0]}] Команда '{cmd}' провалена")
    return False


def get_height(addr: tuple[str, int]) -> int | None:
    """Вернёт высоту Tello в сантиметрах (0–300) или None."""
    resp = send_command("height?", addr)
    if resp and resp.endswith("cm"):
        try:
            return int(resp[:-2])
        except ValueError:
            pass
    return None


def battery_check(addr: tuple[str, int]) -> bool:
    """True, если заряд ≥ MIN_BATTERY%."""
    resp = send_command("battery?", addr)
    try:
        level = int(resp)
        with console_lock:
            print(f"[{addr[0]}] Battery: {level}%")
        return level >= MIN_BATTERY
    except (TypeError, ValueError):
        with console_lock:
            print(f"[{addr[0]}] Неразборчивый ответ battery?: '{resp}'")
        return False


# ── основной поток для каждого дрона ───────────────────────────────────
def control_drone(ip: str, port: int = 8889):
    addr = (ip, port)

    # 1. SDK on
    with console_lock:
        print(f"[{ip}] SDK on…")
    if not send_with_retry("command", addr):
        return

    # 2. батарея
    if not battery_check(addr):
        return

    # 3. взлёт и подъём
    if not send_with_retry("takeoff", addr, retries=5, delay=2):
        return
    send_with_retry(f"up {MOVE_DIST}", addr)

    # 4. измеряем высоту и записываем
    my_h = get_height(addr)
    if my_h is None:
        with console_lock:
            print(f"[{ip}] Не удалось получить height? — пропускаю синхронизацию")
    else:
        with heights_lock:
            heights[ip] = my_h
    try:
        barrier.wait(timeout=15)          # ждём всех
    except threading.BrokenBarrierError:
        pass

    # 5. вычисляем целевую высоту (мин)
    with heights_lock:
        target_alt = min(heights.values()) if heights else my_h or 0

    # 6. корректируемся, если нужно
    if my_h is not None:
        diff = target_alt - my_h
        if abs(diff) > ALT_TOLER:
            cmd = "up" if diff > 0 else "down"
            send_with_retry(f"{cmd} {abs(diff)}", addr)
    with console_lock:
        print(f"[{ip}] Высота синхронизирована (≈ {target_alt} см)")

    # 7. управление с клавиатуры
    with console_lock:
        print(f"[{ip}] Управление: WASD/стрелки Q/E Space L")
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
                level = int(send_command("battery?", addr) or 0)
                if level >= 60:
                    send_with_retry("flip f", addr)
                else:
                    with console_lock:
                        print(f"[{ip}] Battery {level}% — флип запрещён")
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


# ── точка входа ─────────────────────────────────────────────────────────
def main():
    global socket_udp, barrier

    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind(("", 9000))         # общий порт

    num = int(input("Сколько дронов подключить? → "))
    ips = asyncio.run(SearchIPAsync.find_connected_drones(num)) or []
    if not ips:
        print("Дроны не найдены.")
        return

    with console_lock:
        print("Найденные IP:", ips)

    barrier = threading.Barrier(len(ips))
    threads = [threading.Thread(target=control_drone, args=(ip,), daemon=True)
               for ip in ips]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    socket_udp.close()


if __name__ == "__main__":
    main()

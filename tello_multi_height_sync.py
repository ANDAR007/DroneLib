"""tello_multi_height_sync.py
Управление группой DJI Tello через отдельные UDP‑сокеты
+ автоматическое выравнивание высоты.

• Для каждого дрона создаётся собственный сокет (bind('', 0)),
  поэтому ответы не путаются.
• После взлёта запрашиваем `height?`, берём минимальную высоту
  и корректируем положение всех дронов до неё (±ALT_TOLER см).
• Клавиши:  WASD / ←→↑↓ — движение  |  Q/E — поворот  |  Space — flip
            L — посадка.

Требуется:
    pip install keyboard
"""

import socket
import threading
import time
import keyboard
import asyncio
import SearchIPAsync

# ── настройки ────────────────────────────
MOVE_DIST   = 50      # см за шаг
TURN_ANGLE  = 60      # град за поворот
MIN_BATTERY = 40      # % минимальный заряд
ALT_TOLER   = 10      # см допустимое отклонение

# ── глобальные объекты ───────────────────
console_lock = threading.Lock()

heights: dict[str, int] = {}
heights_lock = threading.Lock()
barrier: threading.Barrier | None = None


# ── утилиты ──────────────────────────────
def send_command(sock: socket.socket, cmd: str,
                 addr: tuple[str, int], timeout: float = 5) -> str | None:
    """Отправить команду и вернуть ответ этого же дрона, либо None."""
    deadline = time.time() + timeout
    sock.sendto(cmd.encode(), addr)
    while time.time() < deadline:
        sock.settimeout(deadline - time.time())
        try:
            data, src = sock.recvfrom(1024)
        except socket.timeout:
            return None
        if src == addr:                  # фильтруем «чужие» пакеты
            return data.decode().strip()
    return None


def send_with_retry(cmd: str, sock: socket.socket, addr: tuple[str, int],
                    retries: int = 3, delay: float = 1) -> bool:
    for attempt in range(1, retries + 1):
        resp = send_command(sock, cmd, addr)
        if resp == 'ok':
            with console_lock:
                print(f"[{addr[0]}] '{cmd}' — ok")
            return True
        with console_lock:
            print(f"[{addr[0]}] Попытка {attempt}: '{cmd}' → '{resp}'")
        time.sleep(delay)
    with console_lock:
        print(f"[{addr[0]}] Команда '{cmd}' провалена")
    return False


def get_height(sock: socket.socket, addr: tuple[str, int]) -> int | None:
    resp = send_command(sock, 'height?', addr)
    if resp and resp.endswith('cm'):
        try:
            return int(resp[:-2])
        except ValueError:
            pass
    return None


def battery_check(sock: socket.socket, addr: tuple[str, int]) -> bool:
    resp = send_command(sock, 'battery?', addr)
    try:
        level = int(resp)
        with console_lock:
            print(f"[{addr[0]}] Battery: {level}%")
        return level >= MIN_BATTERY
    except (TypeError, ValueError):
        with console_lock:
            print(f"[{addr[0]}] Неразборчивый battery?: '{resp}'")
        return False


# ── поток управления дроном ──────────────
def control_drone(ip: str, port: int = 8889):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))           # уникальный локальный порт
    addr = (ip, port)

    # SDK
    with console_lock:
        print(f"[{ip}] SDK on…")
    if not send_with_retry('command', sock, addr):
        return

    # батарея
    if not battery_check(sock, addr):
        return

    # взлёт + подъём
    if not send_with_retry('takeoff', sock, addr, retries=5, delay=2):
        return
    send_with_retry(f'up {MOVE_DIST}', sock, addr)

    # высота
    my_h = get_height(sock, addr)
    if my_h is not None:
        with heights_lock:
            heights[ip] = my_h
    try:
        barrier.wait(timeout=15)
    except threading.BrokenBarrierError:
        pass

    with heights_lock:
        target_alt = min(heights.values()) if heights else my_h or 0

    if my_h is not None:
        diff = target_alt - my_h
        if abs(diff) > ALT_TOLER:
            cmd = 'up' if diff > 0 else 'down'
            send_with_retry(f'{cmd} {abs(diff)}', sock, addr)
    with console_lock:
        print(f"[{ip}] Высота синхронизирована ≈ {target_alt} см")

    # клавиатура
    with console_lock:
        print(f"[{ip}] WASD/стрелки Q/E Space L")

    try:
        while True:
            if keyboard.is_pressed('w'):
                send_with_retry(f'forward {MOVE_DIST}', sock, addr)
            elif keyboard.is_pressed('s'):
                send_with_retry(f'back {MOVE_DIST}', sock, addr)
            elif keyboard.is_pressed('a'):
                send_with_retry(f'left {MOVE_DIST}', sock, addr)
            elif keyboard.is_pressed('d'):
                send_with_retry(f'right {MOVE_DIST}', sock, addr)
            elif keyboard.is_pressed('up'):
                send_with_retry(f'up {MOVE_DIST}', sock, addr)
            elif keyboard.is_pressed('down'):
                send_with_retry(f'down {MOVE_DIST}', sock, addr)
            elif keyboard.is_pressed('q'):
                send_with_retry(f'ccw {TURN_ANGLE}', sock, addr)
            elif keyboard.is_pressed('e'):
                send_with_retry(f'cw {TURN_ANGLE}', sock, addr)
            elif keyboard.is_pressed('b'):
                battery_check(sock, addr)
            elif keyboard.is_pressed('space'):
                level = int(send_command(sock, 'battery?', addr) or 0)
                if level >= 60:
                    send_with_retry('flip f', sock, addr)
                else:
                    with console_lock:
                        print(f"[{ip}] Battery {level}% — флип запрещён")
            elif keyboard.is_pressed('l'):
                send_with_retry('land', sock, addr)
                with console_lock:
                    print(f"[{ip}] Посадка выполнена")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        send_with_retry('land', sock, addr)
        with console_lock:
            print(f"[{ip}] Аварийная посадка (Ctrl+C)")


# ── main ─────────────────────────────────
def main():
    global barrier
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


if __name__ == "__main__":
    main()

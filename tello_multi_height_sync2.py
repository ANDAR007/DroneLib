import socket
import threading
import time
import keyboard
import asyncio
import SearchIPAsync

MOVE_DIST   = 50
TURN_ANGLE  = 60
MIN_BATTERY = 40

console_lock = threading.Lock()


def send_command(sock: socket.socket, cmd: str, addr: tuple[str, int], timeout: float = 5) -> str | None:
    sock.sendto(cmd.encode(), addr)
    deadline = time.time() + timeout
    while time.time() < deadline:
        sock.settimeout(deadline - time.time())
        try:
            data, src = sock.recvfrom(1024)
        except socket.timeout:
            return None
        if src == addr:
            return data.decode().strip()
    return None

def send_with_retry(cmd: str, sock: socket.socket, addr: tuple[str, int], retries: int = 5, delay: float = 1) -> bool:
    for attempt in range(1, retries + 1):
        resp = send_command(sock, cmd, addr)
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

def battery_ok(sock: socket.socket, addr: tuple[str, int]) -> bool:
    resp = send_command(sock, "battery?", addr)
    try:
        level = int(resp)
        with console_lock:
            print(f"[{addr[0]}] Battery: {level}%")
        return level >= MIN_BATTERY
    except (TypeError, ValueError):
        with console_lock:
            print(f"[{addr[0]}] battery? непонятно: '{resp}'")
        return False


def control_drone(ip: str, port: int = 8889):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    addr = (ip, port)

    with console_lock:
        print(f"[{ip}] SDK on…")
    if not send_with_retry("command", sock, addr):
        return

    if not battery_ok(sock, addr):
        return

    if not send_with_retry("takeoff", sock, addr, retries=5, delay=2):
        return
    send_with_retry(f"up {MOVE_DIST}", sock, addr)

    with console_lock:
        print(f"[{ip}] WASD/стрелки Q/E Space B L")

    try:
        while True:
            # движение
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
            # повороты
            elif keyboard.is_pressed('q'):
                send_with_retry(f'ccw {TURN_ANGLE}', sock, addr)
            elif keyboard.is_pressed('e'):
                send_with_retry(f'cw {TURN_ANGLE}', sock, addr)
            # флип
            elif keyboard.is_pressed('space'):
                send_with_retry('flip f', sock, addr)
            # сценарный вариант полета (полет по плану (P))
            elif keyboard.is_pressed('p'):
                print(f"[{ip}] Запуск полета в режиме сценария")
                send_with_retry(f'forward {MOVE_DIST}', sock, addr)
                send_with_retry(f'cw 120', sock, addr)

                send_with_retry(f'forward {MOVE_DIST}', sock, addr)
                send_with_retry(f'cw 120', sock, addr)

                send_with_retry(f'forward {MOVE_DIST}', sock, addr)
                send_with_retry(f'cw 120', sock, addr)  # Можно опустить, если посадка

                print(f"[{ip}] Сценарий закончен!")
            # вывод батареи
            elif keyboard.is_pressed('b'):
                resp = send_command(sock, 'battery?', addr)
                with console_lock:
                    print(f"[{ip}] Battery now: {resp}%")
                time.sleep(0.3)  # debounce
            # посадка
            elif keyboard.is_pressed('l'):
                send_with_retry('land', sock, addr)
                with console_lock:
                    print(f"[{ip}] Посадка выполнена")
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        send_with_retry('land', sock, addr)
        with console_lock:
            print(f"[{ip}] Аварийная посадка (Ctrl+C)")


def main():
    num = int(input("Сколько дронов подключить? → "))
    ips = asyncio.run(SearchIPAsync.find_connected_drones(num)) or []
    if not ips:
        print("Дроны не найдены.")
        return
    with console_lock:
        print("Найденные IP:", ips)

    threads = []
    for idx, ip in enumerate(ips):
        t = threading.Thread(target=control_drone, args=(ip,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.3 * (idx + 1))
#стартовать в другом цикле
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
#
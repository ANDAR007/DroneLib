import socket
import threading
import time
import keyboard
import asyncio
import SearchIPAsync

# Консольная блокировка
console_lock = threading.Lock()

# Общий UDP-сокет для всех команд (биндим в main)
socket_udp = None


def send_command(command, addr, timeout=5):
    """
    Отправляет команду через заранее бинденый UDP-сокет и ждёт ответ.
    """
    try:
        socket_udp.settimeout(timeout)
        socket_udp.sendto(command.encode('utf-8'), addr)
        response, _ = socket_udp.recvfrom(1024)
        return response.decode('utf-8')
    except Exception as e:
        with console_lock:
            print(f"[{addr[0]}] Ошибка '{command}': {e}")
        return None


def send_with_retry(command, addr, retries=3, delay=1):
    """
    Повторяет отправку команды до получения 'ok' или исчерпания попыток.
    """
    for attempt in range(1, retries + 1):
        response = send_command(command, addr)
        if response == 'ok':
            with console_lock:
                print(f"[{addr[0]}] Команда '{command}' — ok")
            return True
        with console_lock:
            print(f"[{addr[0]}] Попытка {attempt}: команда '{command}' не удалась, ответ='{response}'")
        time.sleep(delay)
    with console_lock:
        print(f"[{addr[0]}] Команда '{command}' провалена после {retries} попыток")
    return False


def battery_check(addr, retries=3):
    """
    Проверяет уровень батареи, возвращает True, если >=40%.
    """
    for _ in range(retries):
        resp = send_command('battery?', addr)
        try:
            level = int(resp)
            with console_lock:
                print(f"[{addr[0]}] Battery: {level}%")
            return level >= 40
        except (TypeError, ValueError):
            with console_lock:
                print(f"[{addr[0]}] Не удалось прочитать батарею, ответ='{resp}' — повторяем")
            time.sleep(1)
    with console_lock:
        print(f"[{addr[0]}] Не удалось проверить батарею после {retries} попыток")
    return False


def control_drone(ip, port=8889):
    addr = (ip, port)

    # Активируем SDK
    with console_lock:
        print(f"[{ip}] Включаем SDK...")
    if not send_with_retry('command', addr, retries=3, delay=1):
        return

    # Проверяем батарею и взлетаем
    if not battery_check(addr):
        return
    if send_with_retry('takeoff', addr, retries=5, delay=2):
        with console_lock:
            print(f"[{ip}] Взлет успешно!")
    else:
        return

    # Поднимаем на 50 см
    send_with_retry('up 50', addr)

    with console_lock:
        print(f"[{ip}] Управление: WASD=движение, ↑↓=вверх/вниз, Q/E=повороты, пробел=флип, L=посадка")

    try:
        while True:
            if keyboard.is_pressed('w'):
                send_with_retry('forward 50', addr)
            elif keyboard.is_pressed('s'):
                send_with_retry('back 50', addr)
            elif keyboard.is_pressed('a'):
                send_with_retry('left 50', addr)
            elif keyboard.is_pressed('d'):
                send_with_retry('right 50', addr)
            elif keyboard.is_pressed('up'):
                send_with_retry('up 50', addr)
            elif keyboard.is_pressed('down'):
                send_with_retry('down 50', addr)
            elif keyboard.is_pressed('q'):
                send_with_retry('ccw 60', addr)
            elif keyboard.is_pressed('e'):
                send_with_retry('cw 60', addr)
            elif keyboard.is_pressed('space'):
                send_with_retry('flip f', addr)
            elif keyboard.is_pressed('l'):
                send_with_retry('land', addr)
                with console_lock:
                    print(f"[{ip}] Посадка выполнена")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        send_with_retry('land', addr)
        with console_lock:
            print(f"[{ip}] Аварийная посадка (Ctrl+C)")


def main():
    global socket_udp
    pc_ip = ''  # слушаем на всех интерфейсах
    pc_port = 9000

    # Создаём и привязываем UDP-сокет
    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind((pc_ip, pc_port))

    num = int(input("Сколько дронов подключить? "))
    ips = asyncio.run(SearchIPAsync.find_connected_drones(num))
    if not ips:
        print("Дроны не найдены.")
        return

    with console_lock:
        print("Найденные IP:", ips)

    threads = []
    for ip in ips:
        t = threading.Thread(target=control_drone, args=(ip,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    socket_udp.close()

if __name__ == '__main__':
    main()
# робит ток с одним
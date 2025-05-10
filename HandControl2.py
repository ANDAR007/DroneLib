import socket
import time
import asyncio
import keyboard
import threading
import SearchIPAsync

console_lock = threading.Lock()


def send_command(command, addr, timeout=5):
    """
    Отправляет команду БПЛА и получает ответ.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(command.encode('utf-8'), addr)
            response, _ = sock.recvfrom(1024)
            return response.decode('utf-8')
    except Exception as e:
        # with console_lock:
        #     print(f"Ошибка при отправке команды '{command}' на {addr}: {e}")
        return None

def send_with_retry(command, socket_udp, addr, retries=3, delay=1):
    for _ in range(retries):
        response = send_command(command, socket_udp, addr)
        if response == 'ok':
            return True
        print(f"Retrying command '{command}'...")
        time.sleep(delay)
    print(f"Command '{command}' failed after {retries} attempts.")
    return False


def control_drone(ip, port=8889):
#    Управление одним БПЛА.
    addr = (ip, port)

    # Включаем режим SDK
    print(f"Отправка команды 'command' на {ip}...")
    send_command("command", addr)
    time.sleep(2)  # Ожидание перед следующими командами

    # Взлет
    print(f"Отправка команды 'takeoff' на {ip}...")
    response = send_command("takeoff", addr, timeout=10)
    print(f"ответ: {response}")
    time.sleep(3)  # стаб дрона

    # Поднимаем дрон на 50 см
    send_command("up 50", addr)

    print("ГОТОВ К УПРАВЛЕНИЮ!")

    while True:
        if keyboard.is_pressed("w"):
            print("Дрон летит вперёд")
            send_command("forward 50", addr)

        if keyboard.is_pressed("s"):
            print("Дрон летит назад")
            send_command("back 50", addr)

        if keyboard.is_pressed("a"):
            print("Дрон летит влево")
            send_command("left 50", addr)

        if keyboard.is_pressed("d"):
            print("Дрон летит вправо")
            send_command("right 50", addr)

        if keyboard.is_pressed("up"):
            print("Дрон поднимается вверх")
            send_command("up 50", addr)

        if keyboard.is_pressed("down"):
            print("Дрон опускается вниз")
            send_command("down 50", addr)

        if keyboard.is_pressed("q"):
            print("Дрон поворачивается влево")
            send_command("ccw 60", addr)

        if keyboard.is_pressed("e"):
            print("Дрон поворачивается вправо")
            send_command("cw 60", addr)

        if keyboard.is_pressed("space"):
            print("Дрон делает флип вперёд")
            send_command("flip f", addr)

        if keyboard.is_pressed("l"):
            print("Посадка дрона...")
            send_command("land", addr)
            # send_command('battery?', addr)
            # battery_response = battery_level = int(battery_response)
            # print(f"ip {addr} Battery: {battery_level}%")
            break


        time.sleep(0.1)
    print("Соединение закрыто.")


def receive_all(sock: socket.socket, count: int) -> bytes:
    buf = b""
    while len(buf) < count:
        new_buf = sock.recv(count - len(buf))
        if not new_buf:
            break
        buf += new_buf
    return buf


def main():
    num_drones = int(input("Введите количество дронов для подключения: "))
    drone_ips = asyncio.run(SearchIPAsync.find_connected_drones(num_drones))


    if not drone_ips:
        print("Не удалось найти дроны!")
        return

    print(f"Подключённые дроны: {drone_ips}")

    if len(drone_ips) == 1:
        control_drone(drone_ips[0])
    else:
        threads = []
        for ip in drone_ips:
            thread = threading.Thread(target=control_drone, args=(ip,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


if __name__ == "__main__":
    main()

# Управление:
# WASD — движение
# Стрелки — вверх/вниз
# Q/E — повороты
# Пробел — флип
# L — посадка
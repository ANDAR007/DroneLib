import SearchIPAsync
import socket
import asyncio
import keyboard
import threading
import time

# Блокировка для вывода на консоль
console_lock = threading.Lock()

# Функция отправки команды с повторными попытками
async def send_command(command, addr, retries=2, timeout=5):
    """
    Асинхронно отправляет команду дрону с повторными попытками.
    """
    for attempt in range(retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                sock.sendto(command.encode('utf-8'), addr)
                response, _ = sock.recvfrom(1024)
                decoded_response = response.decode('utf-8')
                if decoded_response == 'unactive':
                    print(f"Дрон {addr} неактивен")
                    return None
                return decoded_response
        except socket.timeout:
            print(f"Попытка {attempt+1}: Таймаут при отправке '{command}' на {addr}")
        except Exception as e:
            print(f"Ошибка при отправке '{command}' на {addr}: {e}")
    return None

# Функция повторной отправки команды
def send_with_retry(command, socket_udp, addr, retries=3):
    for _ in range(retries):
        response = send_command(command, socket_udp, addr)
        if response == 'ok':
            with console_lock:
                print(f"Command: {command}%")
            return True
        with console_lock:
            print(f"Retrying command '{command}'...")
    with console_lock:
        print(f"Command '{command}' failed after {retries} attempts.")
    return False

async def control_drone(ip, port=8889):
    """
    Управление дроном: инициализация, обработка команд с клавиатуры.
    """
    addr = (ip, port)
    commands = ["command", "battery?", "takeoff"]

    for command in commands:
        print(f"Отправка команды '{command}' на {ip}...")
        # if command == "battery?":
        #     send_with_retry(command, addr)
        #     continue
        response = await send_command(command, addr)
        if response:
            print(f"Ответ от дрона: {response}")

    print("ГОТОВ К УПРАВЛЕНИЮ")

    while True:
        try:
            if keyboard.is_pressed("left"):
                print("< Дрон летит вперед...")
                await send_command("forward 100", addr)
                time.sleep(0.5)

            if keyboard.is_pressed("right"):
                print("> Дрон летит назад...")
                await send_command("back 100", addr)
                time.sleep(0.5)

            if keyboard.is_pressed("up"):
                print("<^> Дрон делает сальто...")
                await send_command("flip f", addr)
                time.sleep(0.5)

            if keyboard.is_pressed("down"):
                print("(!) Посадка дрона...")
                await send_command("land", addr)
                break

            await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            print("(!) Принудительное завершение. Посадка...")
            await send_command("land", addr)
            break

async def main():
    """
    Основная логика: поиск дронов и запуск управления.
    """
    num_drones = 1  # Количество дронов
    drone_ips = await SearchIPAsync.find_connected_drones(num_drones)

    tasks = [control_drone(ip) for ip in drone_ips]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

import SearchIPAsync
import socket
import time
import asyncio

def send_command(command, addr):
    """
    Отправляет команду на указанный IP-адрес дрона.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # if command.encode=='battery?':
            #     sock.sendto(command, addr)
            #     response, _ = sock.recvfrom(1024)
            #     return response
            # else:
            sock.settimeout(15)
            sock.sendto(command.encode('utf-8'), addr)
            response, _ = sock.recvfrom(1024)
            if response == b'unactive':
                print(f"Дрон {addr} неактивен")
                return False
            return response.decode('utf-8')
    except Exception as e:
        print(f"Ошибка при отправке команды '{command}' на {addr}: {e}")
        return None

def control_drone(ip, port=8889):
    """
    Управление дроном: взлет, полет вперед, назад и посадка.
    """
    addr = (ip, port)
    # commands = ["command", "takeoff", "forward 100", "back 100", "land"]
    commands = ["command", "battery?", "takeoff", "land"]

    for command in commands:
        print(f"Отправка команды '{command}' на {ip}...")
        response = send_command(command, addr)
        if response is not None:
            print(f"Ответ от дрона: {response}")
        # if response == "unactive":
        #     return False
        # time.sleep(1)  # Задержка между командами

def main():
    num_drones = 4  # Количество дронов, которые нужно найти
    drone_ips = asyncio.run(SearchIPAsync.find_connected_drones(num_drones))
    # drone_ips = ["192.168.137.117", "192.168.137.206"]
    # ip123 = "192.168.137.5"
    # port123 = 8889
    # ip_and_port = (ip123, port123)
    # # print(send_command("command", ip_and_port))
    # print(send_command("battery?", ip_and_port))

    for ip in drone_ips:
        print(f"Управление дроном с IP {ip}")
        control_drone(ip)


#Сделать управление с клавиатуры, подключить видеопоток.
# LED панель подключить
#подключить 5 дронов
if __name__ == "__main__":
    main()

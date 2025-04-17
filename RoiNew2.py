import socket
import threading
import SearchIPold

# Блокировка для вывода на консоль
console_lock = threading.Lock()

def emergency_land(socket_udp, addr):
    with console_lock:
        print("Emergency landing initiated!")
    socket_udp.sendto(b'land', addr)


def send_command(command, socket_udp, addr):
    try:
        socket_udp.sendto(command.encode('utf-8'), addr)
        response, _ = socket_udp.recvfrom(1024)
        return response.decode('utf-8')
    except Exception as e:
        with console_lock:
            print(f"Error sending command '{command}': {e}")
        return None


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


def battery_check(socket_udp, addr, retries=3):
    for _ in range(retries):
        try:
            battery_response = send_command('battery?', socket_udp, addr)
            battery_level = int(battery_response)
            if battery_level >= 40:
                with console_lock:
                    print(f"Battery: {battery_level}%")
                return True
            else:
                with console_lock:
                    print(f"Low battery level: {battery_level}%. Please recharge.")
                return False
        except ValueError:
            with console_lock:
                print(f"Error reading battery level! Retrying...")
    with console_lock:
        print(f"Failed to read battery level after {retries} attempts.")
    return False


def execute_flight_path(socket_udp, addr, movements):
    for movement in movements:
        if send_with_retry(movement, socket_udp, addr):
            with console_lock:
                print(f"Executed: {movement.capitalize()}")
        else:
            with console_lock:
                print(f"Failed to execute: {movement}")


def drone_control(socket_udp, tello_ip, pc_port, tello_port):
    tello_addr = (tello_ip, tello_port)

    try:
        if send_command('command', socket_udp, tello_addr):
            with console_lock:
                print("SDK mode enabled.")
            if battery_check(socket_udp, tello_addr):
                if send_with_retry('takeoff', socket_udp, tello_addr):
                    if send_with_retry('flip f', socket_udp, tello_addr):
                        if send_with_retry('back 30', socket_udp, tello_addr):

                            send_command('land', socket_udp, tello_addr)
                            battery_check(socket_udp, tello_addr)
                            with console_lock:
                                print(f'Дрон {tello_ip} садится')
                        else:
                            with console_lock:
                                print("Not working: back")
                    else:
                        with console_lock:
                            print("Not working: flip")
                else:
                    with console_lock:
                        print("Not working: takeoff")
            else:
                with console_lock:
                    print("Not working: bat")
        else:
            with console_lock:
                print("Failed to enter SDK mode.")
    except Exception as e:
        with console_lock:
            print(f"An error occurred: {e}")
        battery_check(socket_udp, tello_addr)


def main():
    pc_ip = ''
    pc_port = 9000
    num_drones = 1
    lo_ip = SearchIPold.find_connected_drones(num_drones)
    print(lo_ip)

    # Отладочное сообщение для проверки найденных IP-адресов
    with console_lock:
        print(f"Подключенные дроны: {lo_ip}")

    if len(lo_ip) != num_drones:
        return False #завершаем
        with console_lock:
            print('Не удалось подключить все дроны')
        # Продолжаем работу с найденными дронами
        if not lo_ip:
            with console_lock:
                print('Ни один дрон не найден. Завершение работы.')
            return False
    else:
        with console_lock:
            print('Все дроны подключены')

    tello_port = 8889

    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind((pc_ip, pc_port))

    threads = []
    for tello_ip in lo_ip:
        thread = threading.Thread(target=drone_control, args=(socket_udp, tello_ip, pc_port, tello_port))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    socket_udp.close()


if __name__ == "__main__":
    main()
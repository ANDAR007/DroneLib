import socket
import time


def emergency_land(socket_udp, addr):
    print("Emergency landing initiated!")
    socket_udp.sendto(b'land', addr)


def send_command(command, socket_udp, addr):
    try:
        socket_udp.sendto(command.encode('utf-8'), addr)
        response, _ = socket_udp.recvfrom(1024)
        return response.decode('utf-8')
    except Exception as e:
        print(f"Error sending command '{command}': {e}")
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


def battery_check(socket_udp, addr):
    try:
        battery_response = send_command('battery?', socket_udp, addr)
        battery_level = int(battery_response)
        if battery_level >= 40:
            print(f"Battery: {battery_level}%")
            return True
        else:
            print(f"Low battery level: {battery_level}%. Please recharge.")
            return False
    except ValueError:
        print(f"Error reading battery level!")
        return False


def execute_flight_path(socket_udp, addr, movements):#, delay=1):
    for movement in movements:
        if send_with_retry(movement, socket_udp, addr):
            print(f"Executed: {movement.capitalize()}")
        else:
            print(f"Failed to execute: {movement}")
        # time.sleep(delay)


def main():
    pc_ip = ''
    pc_port = 9000
    tello_ip = '192.168.10.1'
    tello_port = 8889
    tello_addr = (tello_ip, tello_port)

    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind((pc_ip, pc_port))

    try:
        if send_command ('command',socket_udp, tello_addr):
            print("SDK mode enabled.")

            if send_with_retry("ap DroneSwarm kafprog1", socket_udp, tello_addr):
                battery_check(socket_udp, tello_addr)
                print('conect!')
            else:
                print("not conecting to WIFI 1 drone")
        else:
            print("Failed to enter SDK mode.")
    except Exception as e:
        print(f"An error occurred: {e}")
        emergency_land(socket_udp, tello_addr)
    finally:
        socket_udp.close()


if __name__ == "__main__":
    main()

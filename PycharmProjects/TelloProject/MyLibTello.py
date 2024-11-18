import socket


def send_command(command, socket, addr):
    try:
        socket.sendto(command.encode('utf-8'), addr)
        response, _ = socket.recvfrom(1024)
        return response.decode('utf-8')
    except Exception as e:
        print(f"Error sending command '{command}': {e}")
        return None


def emergency_land(socket, addr):
    print("Emergency landing initiated!")
    socket.sendto(b'land', addr)


def send_with_retry(command, socket, addr, retries=3):
    for _ in range(retries):
        response = send_command(command, socket, addr)
        if response == 'ok':
            return True
        print(f"Retrying command '{command}'...")
    print(f"Command '{command}' failed after {retries} attempts.")
    return False


def main():
    pc_ip = ''
    pc_port = 9000
    tello_ip = '192.168.10.1'
    tello_port = 8889
    tello_addr = (tello_ip, tello_port)

    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind((pc_ip, pc_port))

    try:
        if send_with_retry('command', socket_udp, tello_addr):
            print("SDK mode enabled.")

            battery = send_command('battery?', socket_udp, tello_addr)
            print(f"Battery: {battery}%")
            send_command('EXT led 255 0 0', socket_udp, tello_addr)
            send_command('EXT mled l r 1 takeoff', socket_udp, tello_addr)

            if send_with_retry('takeoff', socket_udp, tello_addr):
                print("Takeoff successful.")

                send_command('EXT led 0 255 0', socket_udp, tello_addr)
                send_command('EXT mled l r 1 fly', socket_udp, tello_addr)
                if send_with_retry('forward 100', socket_udp, tello_addr):
                    print("Moved forward 100.")
                if send_with_retry('right 100', socket_udp, tello_addr):
                    print("Moved forward 100.")
                if send_with_retry('back 100', socket_udp, tello_addr):
                    print("Moved back 100.")
                if send_with_retry('left 100', socket_udp, tello_addr):
                    print("Moved forward 100.")

                if not send_with_retry('land', socket_udp, tello_addr):
                    send_command('EXT led 255 0 0', socket_udp, tello_addr)
                    send_command('EXT mled l r 1 !!!', socket_udp, tello_addr)
                    print("Landing failed!")
                    emergency_land(socket_udp, tello_addr)
            else:
                emergency_land(socket_udp, tello_addr)
                send_command('EXT led 255 0 0', socket_udp, tello_addr)
                send_command('EXT mled l r 1 !!!', socket_udp, tello_addr)
        else:
            print("Failed to enter SDK mode.")
    except Exception as e:
        print(f"An error occurred: {e}")
        emergency_land(socket_udp, tello_addr) #косяк! когда ошибка на соките посылает сигрнал на сокет на прриземление
    finally:
        socket_udp.close()


if __name__ == "__main__":
    main()

import socket # Python
#import time

pc_ip = ''
pc_port = 9000
pc_ip_port = (pc_ip, pc_port)
socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket.bind(pc_ip_port) # socket для отправки команд
tello_ip = '192.168.10.1'
tello_port = 8889
tello_addr = (tello_ip, tello_port)
socket.sendto(b'command', tello_addr) # включить режим SDK
response2, ip = socket.recvfrom(1024)
if response2 == b'ok':
    socket.sendto(b'battery?', tello_addr)  # состояние батареи
    response1, ip = socket.recvfrom(1024)
    print(response1)
    socket.sendto(b'takeoff', tello_addr)  # взлететь
    response1, ip = socket.recvfrom(1024)
    print(response1)
    if response1 == b'ok':
        socket.sendto(b'forward 100', tello_addr)
        print('Вперёд на 100...')
        response1, ip = socket.recvfrom(1024)
        if response1 == b'ok':
            socket.sendto(b'back 100', tello_addr)
            print('назад на 100...')
            if response1 == b'ok':
                socket.sendto(b'land', tello_addr)  # приземлиться
                print('итоговое приземление')
                if response1 == b'ok':
                    socket.sendto(b'battery?', tello_addr)  # состояние батареи
                    response1, ip = socket.recvfrom(1024)
                    print(response1)
                    socket.close()
                else:
                    print('аварийное приземление')
                    socket.sendto(b'land', tello_addr)  # приземлиться
                    socket.close()
            else:
                print('аварийное приземление 4')
                socket.sendto(b'land', tello_addr)  # приземлиться
                socket.close()
        else:
            print('аварийное приземление 3')
            socket.sendto(b'land', tello_addr)  # приземлиться
            socket.close()
    else:
        print('аварийное приземление 2')
        socket.sendto(b'land', tello_addr)  # приземлиться
        socket.close()
else:
    print('аварийное приземление 1')
    socket.sendto(b'land', tello_addr)  # приземлиться
    socket.close()

# socket.sendto(b'takeoff', tello_addr) # взлететь
# response, ip = socket.recvfrom(1024)
# print(response)
# time.sleep(2)
# socket.sendto(b'forward 100', tello_addr)
# print('Вперёд на 100...')
# time.sleep(5)
# # socket.sendto(b'left 100', tello_addr) # полёт по квадрату
# # socket.sendto(b'forward 100', tello_addr)
# # socket.sendto(b'right 100', tello_addr)
# # socket.sendto(b'back 100', tello_addr)
# # socket.sendto(b'left 100', tello_addr)
# socket.sendto(b'back 100', tello_addr)
# response3, ip3 = socket.recvfrom(1024)
# print(response3)
# # time.sleep(5)
# print('Назад на 100...')
# socket.sendto(b'battery?', tello_addr) # состояние батареи
# response1, ip1 = socket.recvfrom(1024)
# print(response1)
# socket.sendto(b'land', tello_addr) # приземлиться
# socket.close()

import socket
import time
import asyncio
import keyboard
import threading
import SearchIPAsync

console_lock = threading.Lock()

# ---------------- TCP→UDP Proxy ----------------

def handle_proxy_client(client_sock, drone_ip, drone_port=8889):
    """
    Принимает от TCP-клиента команды, пересылает их по UDP дрону
    и возвращает ответ обратно по TCP.
    """
    with client_sock, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.settimeout(5)
        udp_addr = (drone_ip, drone_port)
        try:
            while True:
                data = client_sock.recv(1024)
                if not data:
                    break
                # пересылаем на дрон
                udp_sock.sendto(data, udp_addr)
                # ждём ответ и возвращаем TCP-клиенту
                try:
                    resp, _ = udp_sock.recvfrom(1024)
                    client_sock.sendall(resp)
                except socket.timeout:
                    # таймаут, отправляем пустой ответ для обозначения
                    client_sock.sendall(b'')
        except Exception as e:
            print(f"[Proxy] Ошибка: {e}")


def start_tcp_udp_proxy(listen_host, listen_port, drone_ip):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((listen_host, listen_port))
    srv.listen(5)
    print(f"[Proxy] TCP→UDP proxy запущен на {listen_host}:{listen_port}, дрон {drone_ip}:{8889}")
    try:
        while True:
            client, addr = srv.accept()
            print(f"[Proxy] New TCP client from {addr}")
            threading.Thread(
                target=handle_proxy_client,
                args=(client, drone_ip),
                daemon=True
            ).start()
    except KeyboardInterrupt:
        print("[Proxy] Остановка proxy." )
    finally:
        srv.close()

# ---------------- Оригинальный UDP-клиент ----------------

def send_command_udp(command: str, udp_addr, timeout=5):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(command.encode('utf-8'), udp_addr)
            response, _ = sock.recvfrom(1024)
            return response.decode('utf-8')
    except Exception:
        return None


def control_drone_via_udp(drone_ip: str, port=8889):
    udp_addr = (drone_ip, port)
    print(f"[UDP] Отправка 'command' на {drone_ip}...")
    send_command_udp("command", udp_addr)
    time.sleep(2)
    print(f"[UDP] Отправка 'takeoff' на {drone_ip}...")
    resp = send_command_udp("takeoff", udp_addr, timeout=10)
    print(f"[UDP] ответ: {resp}")
    time.sleep(3)
    send_command_udp("up 50", udp_addr)
    print("[UDP] ГОТОВ К УПРАВЛЕНИЮ!")

    while True:
        if keyboard.is_pressed("w"):
            send_command_udp("forward 50", udp_addr)
        if keyboard.is_pressed("s"):
            send_command_udp("back 50", udp_addr)
        if keyboard.is_pressed("a"):
            send_command_udp("left 50", udp_addr)
        if keyboard.is_pressed("d"):
            send_command_udp("right 50", udp_addr)
        if keyboard.is_pressed("up"):
            send_command_udp("up 50", udp_addr)
        if keyboard.is_pressed("down"):
            send_command_udp("down 50", udp_addr)
        if keyboard.is_pressed("q"):
            send_command_udp("ccw 60", udp_addr)
        if keyboard.is_pressed("e"):
            send_command_udp("cw 60", udp_addr)
        if keyboard.is_pressed("space"):
            send_command_udp("flip f", udp_addr)
        if keyboard.is_pressed("l"):
            send_command_udp("land", udp_addr)
            break
        time.sleep(0.1)
    print("[UDP] Управление завершено.")

# ---------------- Объединяем всё в main ----------------

def main():
    mode = input("Выберите режим (proxy/udp): ").strip().lower()
    num = int(input("Введите количество дронов для подключения: "))
    drone_ips = asyncio.run(SearchIPAsync.find_connected_drones(num))

    if not drone_ips:
        print("Не удалось найти дроны!")
        return

    print("Найденные дроны:", drone_ips)

    if mode == 'proxy':
        # Прокси для первого дрона
        listen_host = '0.0.0.0'
        listen_port = 9001
        start_tcp_udp_proxy(listen_host, listen_port, drone_ips[0])
    else:
        # Чистый UDP-клиент для всех найденных дронов
        if len(drone_ips) == 1:
            control_drone_via_udp(drone_ips[0])
        else:
            threads = []
            for ip in drone_ips:
                t = threading.Thread(target=control_drone_via_udp, args=(ip,))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

if __name__ == '__main__':
    main()

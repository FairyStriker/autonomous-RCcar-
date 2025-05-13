#main.py

import tkinter as tk
from RC_GUI import RC_GUI

if __name__ == '__main__':
    ESP_IP = "192.168.0.123"  # 실제 IP로 변경
    ESP_PORT = 8000           # 실제 포트로 변경

    main_root = tk.Tk()
    app = RC_GUI(main_root, ESP_IP, ESP_PORT)
    
    def on_closing():
        print("애플리케이션 종료 중...")
        if hasattr(app, 'stop_current_operations'):
            app.stop_current_operations() # 진행중인 스레드 및 리소스 정리
        if hasattr(app, 'net') and hasattr(app.net, 'close'): # ESP_PC_Network에 close 메소드가 있다면
            app.net.close()
        main_root.destroy()

    main_root.protocol("WM_DELETE_WINDOW", on_closing)
    main_root.mainloop()

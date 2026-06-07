import cv2
import time
import ctypes
import threading

class ThreadedCamera:
    def __init__(self):
        self.cap = None
        self.ret = False
        self.frame = None
        self.stopped = False
        
        # CRITICAL FIX: Frame ID tracker to prevent slow-motion video saving
        self.frame_count = 0 

        for index in [1, 2, 0]:
            self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                ret, frame = self.cap.read()
                if ret:
                    self.ret = ret
                    self.frame = frame
                    self.frame_count += 1
                    break
            
            if self.cap is not None and not self.cap.isOpened():
                self.cap.release()
                self.cap = None

    def start(self):
        if self.cap is not None:
            threading.Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            self.ret, self.frame = self.cap.read()
            if self.ret:
                self.frame_count += 1 # Generate a new unique ID for every fresh hardware frame

    def read(self):
        # Pass the unique frame ID to the UI thread
        return self.ret, self.frame, self.frame_count 

    def stop(self):
        self.stopped = True
        if self.cap is not None:
            self.cap.release()

# 1. Initialize Threaded Hardware Engine
cam = ThreadedCamera().start()

if getattr(cam, 'cap', None) is None:
    ctypes.windll.user32.MessageBoxW(0, "No endoscope detected. Please check the USB connection!", "Hardware Error", 0x10)
    exit()

window_name = "Digital Otoscope System V2.0 - Clinical Trial"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

width = int(cam.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cam.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
if width == 0 or height == 0:
    width, height = 1280, 720

center_x = width // 2
center_y = height // 2

title_line1 = "Ran Ruiqian's Project (Exclusive)"
title_line2 = "Accessible digital otoscope design for clinical teaching"
font = cv2.FONT_HERSHEY_SIMPLEX

size_line1 = cv2.getTextSize(title_line1, font, 0.5, 1)[0]
size_line2 = cv2.getTextSize(title_line2, font, 0.5, 1)[0]

pos_line1 = (width - size_line1[0] - 20, 30)
pos_line2 = (width - size_line2[0] - 20, 55)

success_msg = ">>> SCREENSHOT SAVED <<<"
msg_size = cv2.getTextSize(success_msg, cv2.FONT_HERSHEY_DUPLEX, 0.8, 2)[0]
msg_pos = ((width - msg_size[0]) // 2, height - 50)

screenshot_timer = 0
show_msg_duration = 1.5

# Video Recording Variables
is_recording = False
video_writer = None
last_recorded_frame_count = -1 # Keeps track of what was just written to the file

while True:
    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
        break

    # 2. Fetch frame AND its unique ID
    ret, frame, current_frame_count = cam.read()
    
    if not ret or frame is None:
        ctypes.windll.user32.MessageBoxW(0, "Endoscope signal lost unexpectedly!", "System Warning", 0x10)
        break

    # 3. CRITICAL FIX: Only write to the video file if the frame ID is truly new
    if is_recording and video_writer is not None:
        if current_frame_count != last_recorded_frame_count:
            video_writer.write(frame)
            last_recorded_frame_count = current_frame_count

    display_frame = frame.copy()

    # 4. Draw HUD
    cv2.line(display_frame, (center_x, 0), (center_x, height), (0, 255, 0), 1)
    cv2.line(display_frame, (0, center_y), (width, center_y), (0, 255, 0), 1)
    cv2.circle(display_frame, (center_x, center_y), 80, (0, 255, 0), 1)
    cv2.circle(display_frame, (center_x, center_y), 240, (0, 255, 0), 1)

    cv2.putText(display_frame, title_line1, pos_line1, font, 0.5, (255, 255, 255), 1)
    cv2.putText(display_frame, title_line2, pos_line2, font, 0.5, (200, 200, 200), 1)

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    cv2.putText(display_frame, f"TIME: {current_time}", (20, 40), font, 0.7, (0, 255, 0), 2)
    cv2.putText(display_frame, "Patient ID: TEST-001 | [SPACE]: Photo | [R]: Video | [C]: Colors", (20, 80), font, 0.6, (0, 255, 255), 2)

    if is_recording:
        if int(time.time() * 2) % 2 == 0:
            rec_text = "REC"
            rec_size = cv2.getTextSize(rec_text, font, 1.0, 2)[0]
            cv2.circle(display_frame, (width - rec_size[0] - 60, 100), 10, (0, 0, 255), -1)
            cv2.putText(display_frame, rec_text, (width - rec_size[0] - 40, 107), font, 1.0, (0, 0, 255), 2)

    if time.time() - screenshot_timer < show_msg_duration:
        cv2.putText(display_frame, success_msg, msg_pos, cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow(window_name, display_frame)

    key = cv2.waitKey(1) & 0xFF
    
    if key == 32: 
        filename = f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        threading.Thread(target=cv2.imwrite, args=(filename, frame.copy())).start()
        screenshot_timer = time.time()
        
    elif key == ord('r') or key == ord('R'):
        if not is_recording:
            actual_h, actual_w = frame.shape[:2]
            vid_filename = f"record_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(vid_filename, fourcc, 30.0, (actual_w, actual_h))
            is_recording = True
            last_recorded_frame_count = current_frame_count # Sync ID immediately upon start
        else:
            is_recording = False
            if video_writer is not None:
                video_writer.release()
                video_writer = None

    elif key == ord('c') or key == ord('C'):
        cam.cap.set(cv2.CAP_PROP_SETTINGS, 1)

if is_recording and video_writer is not None:
    video_writer.release()
cam.stop()
cv2.destroyAllWindows()
#must have OpenCv, numpy and matplot lib installed for python
import cv2
import import_json as ij
import data_manipulation as dm
import numpy as np
import math
from matplotlib import pyplot as plt
from pylive import live_plotter
import scipy

#key data
athlete_height = 170 # in cm
camera_fps = 30

#importing json file data
kp = ij.get_keypoints()     #kp is a list of all the 25x3 lists of keypoints
kp = dm.smooth_data(kp, camera_fps)
#kp = ij.interpolate_uncertain_points(kp)       #uncomment to interpolate uncertain points
f_kp = []       #f_kp will be a 25x3 list of the keypoints at a specific frame
speeds=[]

#init
speed = 0
times = 0
new_speed = 0
prev_ang = 0
stride_frames = 0
prev_ankle_distance = 0
direction = 1

#constants
bottom_left_of_screen = (20, 700)
eyes=17
neck=1
hip=8
left_knee=13
right_knee=10
left_ankle=14
right_ankle=11
is_running = True

#get angle between three points
def get_angle(a, b, c):
    ang = math.degrees(math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0]))
    return ang

#function that determines how many pixels correlate to 1 meter, using the height of the athlete
def get_pixels_per_meter(f_kp):   #returns how many pixels correlate to 1 meter in the frame
    coord_eyes = (f_kp[eyes][0], f_kp[eyes][1])
    coord_neck = (f_kp[neck][0], f_kp[neck][1])
    coord_hip = (f_kp[hip][0], f_kp[hip][1])
    coord_knee = (f_kp[left_knee][0], f_kp[left_knee][1])
    coord_ankle = (f_kp[left_ankle][0], f_kp[left_ankle][1])
    distance = 0        #we add the distances between eyes, neck, hip, knee and ankle
    distance += math.dist(coord_eyes, coord_neck)
    distance += math.dist(coord_neck, coord_hip)
    distance += math.dist(coord_hip, coord_knee)
    distance += math.dist(coord_knee, coord_ankle)

    pixels = int(distance/athlete_height*100)
    return pixels

def get_stride_distance(height, is_running):
    if is_running:
        return height*0.011
    else:
        return height*0.00413

#function to draw a meter measurement line on the floor using the athlete's height at a specific frame
def draw_meter_lines(frame, f_kp):
    values = []
    ppm = get_pixels_per_meter(f_kp)
    for keypoint in f_kp:      #we get just the y values
        values.append(keypoint[1])
    max_value = int(max(values))    #we draw the line at the lowest keypoint (approx the floor)
    frame = cv2.line(frame, (0, max_value), (1280, max_value), (255, 255, 255), 2)
    for meter in range(int(1280/ppm)+1):
        frame = cv2.line(frame, (0+(ppm*meter), max_value), (0+(ppm*meter), max_value+10), (255, 255, 255), 3)
        frame = cv2.putText(frame, str(meter), (-10+(ppm*meter), 44 + max_value),cv2.FONT_HERSHEY_SIMPLEX,       # font
                    1,      #font scale
                    (255, 255, 255),   #   font color
                    2)
    return frame

#function to draw circles at the keypoints of a specific frame
def draw_keypoints(frame, f_kp):
    kpid = 0
    for point in f_kp:  # drawing a circle for each kp
        center = (int(point[0]), int(point[1]))
        center_high = ((int(point[0])-5, int(point[1])-15))      #used for writing its id
        frame = cv2.circle(frame, center, 10, (0, 255, 9), 3)       #draws green cirle if certain, red if not
        cv2.putText(frame,
                    str(kpid),
                    center_high,
                    cv2.FONT_HERSHEY_SIMPLEX,  # font
                    0.5,  # font scale
                    (255, 255, 255),  # font color
                    1)  # line type
        kpid += 1
    return frame

#function to draw the athlete speed at the bottom left of the screen of a frame
def draw_athlete_speed(frame, speed):
    cv2.putText(frame,
                str(round(speed, 2)) + ' Km/h',
                bottom_left_of_screen,
                cv2.FONT_HERSHEY_SIMPLEX,
                2,
                (0, 0, 0),
                2)
    return frame


#main
cap = cv2.VideoCapture('video2.MOV')
# Get the Default resolutions
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))

result = cv2.VideoWriter('output.avi',  
cv2.VideoWriter_fourcc('M','J','P','G'),
                         30, (frame_width,frame_height))
frame_count = 0

#Live plotter
size=100
x_vec=np.linspace(0,100,size)
y_vec=[0]*len(x_vec)
line1=[]

while(cap.isOpened()):
    ret, frame = cap.read()
    if not ret:
        break

    try:
        f_kp = kp[frame_count]
    except:
        break

    frame = draw_keypoints(frame, f_kp)

    #here is the algorithm that detects velocity

    hip_coord = (f_kp[hip][0], f_kp[hip][1])
    left_knee_coord = (f_kp[left_knee][0], f_kp[left_knee][1])
    right_knee_coord = (f_kp[right_knee][0], f_kp[right_knee][1])
    ang = direction*get_angle(left_knee_coord, hip_coord, right_knee_coord)

    if ang > (prev_ang):
        stride_frames +=1
        prev_ang = ang
    elif times == 0 or times == 1:
        stride_frames +=1
        times+=1
    else:
        direction*=-1
        prev_ang = -ang
        stride_meters = get_stride_distance(athlete_height,True)
        stride_time = stride_frames * (1 / camera_fps)
        try:
            speed = (stride_meters / stride_time) * 3.6
        except ZeroDivisionError:
            pass
        if speed < 50:
            new_speed=speed - ((speed-new_speed)/4)
        stride_frames=0
        times=0


    #Live plotter
    speeds.append(new_speed)
    y_vec[-1]=speeds[-1]
    #line1 = live_plotter(x_vec, y_vec, line1) #Uncomment this line to show live plotter
    y_vec = np.append(y_vec[1:],new_speed)

    frame = draw_athlete_speed(frame, new_speed)

    cv2.imshow('Running Speed Estimator', frame)
    frame_count += 1
    result.write(frame) 

    if cv2.waitKey(20) & 0xFF == ord('q'):
        break

result.release() 
#Create speed plot
frames=len(kp)
smoothness=int(frames/2) #Change smoothness depending on the video duration

window_length=int(frames/5)
window_length=int(np.ceil(window_length) // 2 * 2 + 1) #Make it an odd number
y=scipy.signal.savgol_filter(speeds, window_length, 2)
x=list(range(1,len(speeds)+1))

x_smooth = np.linspace(min(x),max(x),smoothness)
y_smooth = scipy.interpolate.make_interp_spline(x,y)(x_smooth)
plt.ylabel('Velocity [km/h]')
plt.xlabel('Time [fps]')
plt.title('Running Speed Plot')
plt.plot(x_smooth,y_smooth)
plt.show()

cap.release()
cv2.destroyAllWindows()

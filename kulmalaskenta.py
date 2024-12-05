import numpy as np
import cv2
import mediapipe as mp
import pandas as pd
import math
from scipy.signal import butter, filtfilt

# Alkuasetukset: Valitse puoli ja syöte
side = "right"  # Valitse "left" tai "right"
use_camera = False  # Valitse True, jos haluat käyttää kameraa, tai False, jos käytät tiedostoa
video_file = 'vids/insta/kyykky01_rotated.avi'  # Tiedoston polku, jos käytät videota

# VideoCapture valinta
cap = cv2.VideoCapture(0) if use_camera else cv2.VideoCapture(video_file)

class PoseDetector:
    def __init__(self, mode=False, modelComplex=2, segmentation=False,
                 smooth=True, detectionCon=0.95, trackCon=0.95):
        self.mode = mode
        self.modelComplex = modelComplex
        self.segmentation = segmentation
        self.smooth = smooth
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpDraw = mp.solutions.drawing_utils
        self.mpPose = mp.solutions.pose
        self.pose = self.mpPose.Pose(self.mode, self.modelComplex, self.segmentation,
                                     self.smooth, self.detectionCon, self.trackCon)

    def findPose(self, img, side, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(imgRGB)
        
        if draw and self.results.pose_landmarks:
            joint_ids = {"left": [23, 25, 27], "right": [24, 26, 28]}
            selected_joints = joint_ids[side]
            
            # Värit ja asetukset
            joint_color = (255, 128, 0)  # Sininen sävy nivelpisteille
            line_color = (255, 216, 230)  # Vaaleampi sininen yhdistäville viivoille
            joint_size = 10  # Landmark-pisteiden koko

            # Piirretään lonkan, polven ja nilkan pisteet ja niiden välille viivat
            for id in selected_joints:
                lm = self.results.pose_landmarks.landmark[id]
                h, w, _ = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(img, (cx, cy), joint_size, joint_color, cv2.FILLED)
                
                if id == selected_joints[0]:  # hip
                    hip = (cx, cy)
                elif id == selected_joints[1]:  # knee
                    knee = (cx, cy)
                    cv2.line(img, hip, knee, line_color, 3)  # Vaaleampi sininen viiva
                elif id == selected_joints[2]:  # ankle
                    ankle = (cx, cy)
                    cv2.line(img, knee, ankle, line_color, 3)  # Vaaleampi sininen viiva

        return img

    def findPosition(self, img, draw=True):
        self.lmList = []
        if self.results.pose_landmarks:
            h, w, c = img.shape
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.lmList.append([id, cx, cy])
        return self.lmList

    def calculate_angle(self, x1, y1, x2, y2, x3, y3, side):
        angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - 
                             math.atan2(y1 - y2, x1 - x2))
       
        if side == "left":
            angle = angle - 180
        elif side == "right":
            angle = -(angle - 180)

        return angle

def main():
    detector = PoseDetector()
    data = []

    while True:
        success, img = cap.read()
        if not success:
            break

        img = detector.findPose(img, side=side, draw=True)
        lmList = detector.findPosition(img, draw=False)

        if lmList:
            joint_ids = {"left": [23, 25, 27], "right": [24, 26, 28]}
            hip_id, knee_id, ankle_id = joint_ids[side]
            try:
                hip = lmList[hip_id][1:3]
                knee = lmList[knee_id][1:3]
                ankle = lmList[ankle_id][1:3]

                angle = detector.calculate_angle(
                    hip[0], hip[1],
                    knee[0], knee[1],
                    ankle[0], ankle[1],
                    side=side
                )

                # Näytetään kulma pehmeällä oranssilla
                cv2.putText(img, f'Knee Angle: {int(angle)} deg',
                            (knee[0] - 50, knee[1] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (25, 51, 209), 2)  # Tumma sinenen teksti

                # Tallenna kulma data-listaan
                data.append({'frame': cap.get(cv2.CAP_PROP_POS_FRAMES), 'knee_angle': angle})

            except IndexError:
                pass

        cv2.imshow("Image", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Kulmadatan suodatus ja tallennus
    df = pd.DataFrame(data)
    b, a = butter(4, 6 / (0.5 * 100), btype='low')
    df['filtered_angle'] = filtfilt(b, a, df['knee_angle'])
    df.to_csv(f'results/{side}_knee_angles.csv', index=False)

if __name__ == "__main__":
    main()

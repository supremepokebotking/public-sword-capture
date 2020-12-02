#https://stackoverflow.com/questions/40928205/python-opencv-image-to-byte-string-for-json-transfer
#https://medium.com/@manivannan_data/live-webcam-flask-opencv-python-26a61fee831

from flask import Flask, Response
import cv2
import os
import json
import base64
from flask import Flask
from flask import request
from flask_cors import CORS, cross_origin
import time

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

DEBUG = bool(int(os.environ.get('DEBUG', 0)))
FLASK_PORT = int(os.environ.get('FLASK_PORT', 2204))

video = None
@app.before_first_request
def before_first_request_func():
    print("This function will run once")
    global video
    video = cv2.VideoCapture("/dev/video0")
    #video = cv2.VideoCapture(0)
    video.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    video.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    video.set(cv2.CAP_PROP_BUFFERSIZE, 1);
#camera.set(cv.CAP_PROP_FPS, 2);
#camera.set(cv.CAP_PROP_POS_FRAMES , 1);

def gen(video):
    while True:
        success, image = video.read()
        height , width , layers =  image.shape
        new_h=720
        new_w=1280
        resize = cv2.resize(image, (new_w, new_h))

        ret, buffer = cv2.imencode('.jpg', resize)
        jpg_as_text = base64.b64encode(buffer).decode()
        resp = {
            "image": "data:image/jpeg;base64,"+jpg_as_text
        }
#        cv2.imwrite('lena_opencv_red.jpg', resize)

        return resp

@app.route('/api/video_feed', methods=['GET', 'OPTIONS'])
@cross_origin()
def video_feed():
    print("enter")
    global video
    return Response(response=json.dumps(gen(video)), status=200,mimetype="application/json")

if __name__ == '__main__':
    app.run(debug=True, port=FLASK_PORT, host='0.0.0.0', threaded=True)


def build_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response


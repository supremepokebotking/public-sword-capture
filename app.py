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


def open_cam_usb(dev):
    # We want to set width and height here, otherwise we could just do:
    #     return cv2.VideoCapture(dev)
    gst_str = ("v4l2src device=/dev/video{} ! "
	       "image/jpeg, format=(string)RGGB ! "
	       " jpegdec ! videoconvert ! queue ! appsink").format(dev)
    return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)


video = open_cam_usb("2")
#video = cv2.VideoCapture(0)
video.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
video.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

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

#@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST')
  return response


    # start flask app
if __name__ == '__main__':
    app.run(debug=True, port=FLASK_PORT, host='0.0.0.0', threaded=True)

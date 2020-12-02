from switch_button_press import *
import requests
import enum
from collections import deque
import uuid
import json
import threading
import cv2
import time
import base64
import sys, getopt
import os
import numpy as np

RUNNING = 1
PAUSED = 2
STOPPED = 3
MANUAL_BUTTONS = ['Button A', 'Button B', 'Button X', 'Button Y', 'Button L', 'Button R', 'Button ZL', 'Button ZR', 'LY MAX', 'LY MIN', 'LX MIN', 'LX MAX']

SESSION_TYPE_BATTLE = 1;
SESSION_TYPE_NETWORK = 2;

BATTLE_PROCESS_SESSION_URL = "predict_image";
BATTLE_PROCESS_SESSION_URL = "predict_base64";
NETWORK_PROCESS_SESSION_URL = "network_predict_base64";

BATTLE_CREATE_SESSION_URL = "create_session";

BATTLE_END_SESSION_URL = "end_session";
BATTLE_ABANDON_SESSION_URL = "abandon_session";

DEFAULT_CONFIG = {
    "device": 0,
    "serial_port": '/dev/tty.usbserial-14640',
    "team_label_id": "51ae823f-c24d-47dc-8325-5add2a635e17",
    "ai_style": "randobot",
#    "session_mode": "continuous",
    "battle_style": "network",


    "twitch_channel": "#pokerandoboto",
    "twitch_botname": "PokeHelperBoto",
    "twitch_oauth": "oauth:6lbabeujwmy2l5348tvo05ogjnklvw",
    "trainer_name": "thunder",
    "user_id": "twitch_runner_1",
    "new_team_name": "A new team",
    "use_twitch": True,
    "use_gstream": False,

}

SAVE_MESSAGE_FRAMES = bool(int(os.environ.get('SAVE_MESSAGE_FRAMES', 1)))

BATTLE_FRAMES_dir = 'battle_frames/'
if not os.path.exists(os.path.dirname(BATTLE_FRAMES_dir)):
    os.makedirs(os.path.dirname(BATTLE_FRAMES_dir))

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class MESSAGE_ABILITY_REVEALED(enum.Enum):
    MESSAGE = 0
    PLAYER_ABILITY = 1
    ENEMY_ABILITY = 2

    def get_communicating_rect(self):
        # Style, x1,y1, x2,y2
        if self == MESSAGE_ABILITY_REVEALED.MESSAGE:
            return (1196, 650, 1232, 688)

    def get_rect(self):
        # Style, x1,y1, x2,y2
        if self == MESSAGE_ABILITY_REVEALED.MESSAGE:
            return (106, 585, 1140, 688)
        if self == MESSAGE_ABILITY_REVEALED.PLAYER_ABILITY:
            return (18, 317, 300, 404)
        if self == MESSAGE_ABILITY_REVEALED.ENEMY_ABILITY:
            return (990, 318, 1269, 404)

class RunnerApp():
    def __init__(self, serial_port, user_id):
        self.selectedAction = None
        self.localFrame = None
        self.localMessageFrame = None
        self.waitingForAction = False
        self.running_status = STOPPED
        self.user_id = user_id
        self.session_id = None
        self.service_base_url = "http://localhost:8755"
        self.model_base_url = "https://www.genericterraformtesterurl2.com"
        self.honorable_salad_base_url = "http://localhost:8000"

        self.runSession = False


        self.availableActions = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.observationSpace = []
        self.transcript = ""

        self.aiStyleIndex = 0
        self.aiStyleItems = ["Honorable Salad Ai", "Rando Bot", "Local Service", "Manual Action"]
        self.aiStyle = "randobot"

        self.newTeamName = ""
        self.registeredTeamValue = ""
        self.matchStyle = "Network Match"
        self.matchStyleIndex = 0
        self.matchStyleItems = ["Network Match", "Wild Match", "Trainer Match", "Gym Leader"]
        self.registeredTeam = "Register New Team"
        self.registeredTeamIndex = 0
        self.registeredTeamItems = []
        self.registeredTeamId = None
        self.selectedPokemonNames = []
        self.trainerName = "thunder"
        self.registeredFullPartyNames = []
        self.sshIsConnected = False

        self.botName = "PokeHelperBoto"
        self.oauthToken = "oauth:6lbabeujwmy2l5348tvo05ogjnklvw"
        self.channel = "#pokerandoboto"

        self.isMessagingScanRunning = False
        self.isInBattlePhase = False
        self.message_frames_queue = deque(maxlen=11)
        self.last_message_frame = None

        self.selectedTeamIndex = 0;

        self.inContinuousOnlineBattle = False;
        self.sessionType = None;
        self.performingNetworkRequest = False
        self.wait = 0.2
        self.serial = Serial(serial_port)
        self.message_frame_count = 0


    def fetchConfiguration(self):
        url = self.service_base_url + '/api/get_last_configuration'
        headers = {'content-type': 'application/json'}

        data = {
            'user_id': self.user_id,
        }
        print('fetchConfiguration url:', url)

        data_json = json.dumps(data)
        response = requests.post(url, data=data_json, headers=headers)
        response = json.loads(response.text)
        print('fetchConfiguration data:', response)
        self.aiStyle = response["config"]["aiStyle"]
        self.inferenceServer = response["config"]["aiServerUrl"]
        self.registeredTeamId = response["config"]["registered_team_label"]
        self.matchStyleIndex = response["config"]["match_type"]
        self.webCamName = response["config"]["webCamName"]
        self.trainerName = response["config"]["trainer_name"]


    def fetchRegisteredTeams(self):
        url = self.service_base_url + '/api/get_registered_teams'
        headers = {'content-type': 'application/json'}

        data = {
            'user_id': self.user_id,
        }
        print('fetchRegisteredTeams url:', url)

        data_json = json.dumps(data)
        response = requests.post(url, data=data_json, headers=headers)
        res = json.loads(response.text)
        print('fetchRegisteredTeams data:', res)
        registered_teams = res["teams_info"]
        print('registered_teams data:', registered_teams)
        teamValue = self.registeredTeam
        teamId = self.registeredTeamId

        if len(registered_teams) > 0:
            teamValue = registered_teams[0]["team_rep"]
            teamId = registered_teams[0]["team_label_id"]

        print('Printing Registered Teams')
        for team in registered_teams:
            print('team name: %s, team label id: %s' % (team['team_name'], team['team_label_id']))

        self.registeredTeam = teamValue
        self.registeredTeamId = teamId
        self.registeredTeamItems = registered_teams

    def endSession(self):
        if self.session_id == None:
            print("You need to start a session before ending");
            return

        self.inContinuousOnlineBattle = False;
        self.sessionType = None;

        self.running_status = STOPPED
        self.runSession = False
        self.startSessionEnabled = True
        self.pauseResumeSessionEnabled = False
        self.stopSessionEnabled = False
        self.abandonSessionEnabled = False

        team_name = None
        if self.newTeamName != None:
            team_name  = self.newTeamName;

        data = {
          "user_id": self.user_id,
          "session_id": self.session_id,
          "tags": [],
          "description": "Yet another sample run",
          "team_name": team_name,
          "team_data": self.registeredTeamValue,
        }

        #clear session id
        self.session_id = None;

        url = self.service_base_url + '/api/end_session'
        headers = {'content-type': 'application/json'}

        print('endSession url:', url)

        data_json = json.dumps(data)
        try:
            response = requests.post(url, data=data_json, headers=headers)
            res = json.loads(response.text)
            print('endSession data:', res)
        except Exception:
            self.errors += 1
            print('an error occured. error count: %d' % self.errors)


    def silentEndSession(self):
        if self.session_id == None:
            print("You need to start a session before ending");
            return

        team_name = None
        if self.newTeamName != None:
            team_name  = self.newTeamName;

        data = {
          "user_id": self.user_id,
          "session_id": self.session_id,
          "tags": [],
          "description": "Yet another sample run",
          "team_name": team_name,
          "team_data": self.registeredTeamValue,
        }

        #clear session id
        self.session_id = None;

        url = self.service_base_url + '/api/end_session'
        headers = {'content-type': 'application/json'}

        print('silentEndSession url:', url)

        data_json = json.dumps(data)
        response = requests.post(url, data=data_json, headers=headers)
        res = json.loads(response.text)
        print('silentEndSession data:', res)

    def handleActionForStyle(self):
        print('aistyle for action', self.aiStyle)
        if self.aiStyle == "honorable_salad":
            self.handleHonableAction()
        else:
            #for randobot as well as unimplemented
            self.waitingForAction = False

    def handleHonableAction(self):
        combined = self.observationSpace.extend(self.availableActions);
        slim_data = {
          "obs": combined,
          "valid_moves": self.availableActions,
          "transcript": self.transcript,
        }

        url = self.honorable_salad_base_url + '/api/predict_valid'
        headers = {'content-type': 'application/json'}

        print('handleHonableAction url:', url)

        data_json = json.dumps(data)
        response = requests.post(url, data=data_json, headers=headers)
        res = json.loads(response.text)
        print('handleHonableAction data:', res)
        action = res['action']
        self.swordActionSelected(action)

    def cancelWaitingForAction(self, time_to_wait):
        time.sleep(time_to_wait)
        self.waitingForAction = False

    def swordActionSelected(self, index):
        print('sword action selected', index)
        self.selectedAction = index

    def capture(self, frame):
        self.wait = 0.2
        actionToSend = self.selectedAction
        if self.waitingForAction:
            if self.selectedAction != None:
                self.waitingForAction = False
                self.selectedAction = None
            else:
                if self.runSession:
                    self.wait = 0.1
                self.performingNetworkRequest = False
                return

        message_preapproved = False
        imageSrc = frame

        ret, buffer = cv2.imencode('.jpg', imageSrc)
        imageSrc = "data:image/jpeg;base64,"+base64.b64encode(buffer).decode()

#        imencoded = cv2.imencode(".jpg", imageSrc)[1]
#        file = {'file': ('image', imencoded.tostring(), 'image/jpeg', {'Expires': '0'})}

        slim_data = {
          "image": imageSrc,
          "user_id": self.user_id,
          "session_id": self.session_id,
          "action": actionToSend,
          "message_preapproved": message_preapproved
        }

        sessionUrl = BATTLE_PROCESS_SESSION_URL
        if self.sessionType == SESSION_TYPE_NETWORK:
            sessionUrl = NETWORK_PROCESS_SESSION_URL
            slim_data['team_label_id'] = self.registeredTeamId
            slim_data['party_names'] = self.registeredFullPartyNames

        url = self.service_base_url +'/api/'+sessionUrl
        headers = {'content-type': 'application/json'}
        print('capture url:', url)

        data_json = json.dumps(slim_data, cls=NumpyEncoder)
        response = requests.post(url, data=data_json, headers=headers)
#        response = requests.post(url, files=file, data=data_json, headers=headers)
        res = json.loads(response.text)

        self.wait = res['wait_threshold']

        if 'extra_info' in res:
            extra_info = res['extra_info']
            print('extra_info', extra_info);
            self.waitingForAction = False

            if 'is_expecting_action' in extra_info:
                self.waitingForAction = extra_info['is_expecting_action']

            if 'team_info' in extra_info:
                team_info = extra_info['team_info']
                print('team_info', team_info);
                self.registeredTeamValue = team_info

            if 'twitch_summary' in extra_info:
                twitch_summary = extra_info['twitch_summary']
                print('twitch_summary', twitch_summary);

            #Only show these messages if we will prompt chat for action
            if 'twitch_battle_summary' in extra_info:
                twitch_battle_summary = extra_info['twitch_battle_summary']
                print('twitch_battle_summary', twitch_battle_summary);

            if 'frame_rejected' in extra_info:
                frame_rejected = extra_info['frame_rejected']
                print('frame_rejected:', frame_rejected);

            if 'no_delay' in extra_info:
                no_delay = extra_info['no_delay'];

            if 'is_battle_phase' in extra_info:
                is_battle_phase = extra_info['is_battle_phase']
                print('is_battle_phase', is_battle_phase);
                self.isInBattlePhase = is_battle_phase
                if self.isInBattlePhase:
                    self.wait = 0

            forced_cooldown = False
            if 'forced_cooldown' in extra_info:
                forced_cooldown = extra_info['forced_cooldown']

            # if not first time and ai is twitch, skip interaction to save time.
            first_time_picking_action = True
            if 'first_time_picking_action' in extra_info:
                first_time_picking_action = extra_info['first_time_picking_action']


            # 10 seconds to finish
            ACTION_TIMEOUT = 10
            if self.waitingForAction:
                self.selectedAction = None
                self.availableActions = extra_info['valid_moves']
                self.observationSpace = extra_info['combined']
                self.transcript = extra_info['transcript']


                self.handleActionForStyle();
                t = threading.Thread(target=self.cancelWaitingForAction, args=[ACTION_TIMEOUT])
                t.start()
                self.performingNetworkRequest = False
                return

            action = None
            if 'action' in res and res['action'] is not None:
                action = res['action'];
                print('action', action);

                button_wait = 0.2
                if action == 'Button A':
                    button_wait = 0.67
                    # Getting old frames for network mode, need more delay for web
                    if self.sessionType == SESSION_TYPE_NETWORK:
                        button_wait = 0.8
                if self.sessionType == SESSION_TYPE_BATTLE and self.isInBattlePhase:
                    button_wait = 0.13
#                if no_delay:
#                    pass
    #                button_wait = 100
                if forced_cooldown == True:
                    print('cooling a down a bit')
                    button_wait = 360

                self.serial.send(action)
                print(res['extra_info']);
                self.wait = button_wait
            elif not res['done']:
                self.performingNetworkRequest = False
                return

        if res['done']:
            print('Look at that form, session ended.')
            self.running_status = STOPPED
            self.isMessagingScanRunning = False
            self.isInBattlePhase = False
            self.runSession = False

            # wait 3 seconds to allow for previous session to end.
            SESSION_SWITCH_TIMEOUT = 3
            if self.inContinuousOnlineBattle:
                if self.sessionType == SESSION_TYPE_BATTLE:
                    self.silentEndSession();
                    # can get away with this because
                    self.createSilentNetworkSession(SESSION_SWITCH_TIMEOUT)
                else:
                    print(res['extra_info']);
                    registeredTeamId = None
                    selectedPokemonNames = []
                    registeredFullPartyNames = []

                    if extra_info['team_label_id'] is not None:
                        registeredTeamId = extra_info['team_label_id'];

                    if extra_info['selected_pkmn_names'] is not None:
                        selectedPokemonNames = extra_info['selected_pkmn_names'];

                    if extra_info['party_full_names'] is not None:
                        registeredFullPartyNames = extra_info['party_full_names'];

                    self.registeredTeamId = registeredTeamId
                    self.selectedPokemonNames = selectedPokemonNames
                    self.registeredFullPartyNames = registeredFullPartyNames

                    self.createSilentSingleSession(SESSION_SWITCH_TIMEOUT)
            else:
                if self.sessionType == SESSION_TYPE_BATTLE:
                    self.endSession()
        self.performingNetworkRequest = False

    def createSilentSingleSession(self, time_to_wait):
        print("createSilentSingleSession")
        time.sleep(time_to_wait)
        self.inContinuousOnlineBattle = True;
        self.sessionType = SESSION_TYPE_BATTLE

        self.session_id = None
        self.runSession = False
        self.stopSessionEnabled = True
        self.abandonSessionEnabled = True
        self.pauseResumeSessionEnabled = True
        self.startSessionEnabled = False

        self.createNewSession()

    def oneTimeSetupCreateSilentNetworkSession(self):
        valueIndex = 0
        matchStyleValue = self.matchStyleItems[valueIndex]

        self.matchStyle = matchStyleValue
        self.matchStyleIndex = valueIndex
        self.registeredTeamId = None
        self.registeredFullPartyNames = None

        self.createSilentNetworkSession(time_to_wait=1)

    def createSilentNetworkSession(self, time_to_wait):
        print("createSilentNetworkSession")
        time.sleep(time_to_wait)
        # clear session id
        self.inContinuousOnlineBattle = True;
        self.sessionType = SESSION_TYPE_NETWORK
        self.session_id = str(uuid.uuid4())
        self.runSession = True

    def createNewSession(self):
        if self.session_id is not None:
            print("You need to end a session before beginning a new one., session undefined");
            return

        if self.running_status != STOPPED:
            print("You need to end a session before beginning a new one., running status not stopped");
            return

        team_id = None
        if self.registeredTeamIndex > 0:
            team_id = self.registeredTeamId

        # Continuous sessions have different rules, just pass along.
        if self.inContinuousOnlineBattle:
            team_id = self.registeredTeamId

        selected_pokemon_names = self.selectedPokemonNames

        trainer_name = None

        if self.trainerName is not None:
            trainer_name = self.trainerName

        slim_data = {
          "user_id": self.user_id,
          "trainer_name": trainer_name,
          "match_type": self.matchStyleIndex,
          "registered_team_label": team_id,
          "aiStyle": self.aiStyle,
          "aiServerUrl": self.inferenceServer,
          "webCamName": self.webCamName,
          "selected_pokemon_names": selected_pokemon_names,
        }
        print('slim_data', slim_data)

        url = self.service_base_url + '/api/create_session'
        headers = {'content-type': 'application/json'}

        print('createNewSession url:', url)

        data_json = json.dumps(slim_data)
        response = requests.post(url, data=data_json, headers=headers)
        res = json.loads(response.text)
        print('createNewSession data:', res)
        self.session_id = res['session_id']
        self.running_status = RUNNING
        self.runSession = True


width = 1920
height = 1080

gst_str = ('nvarguscamerasrc ! ' + 'video/x-raw(memory:NVMM), ' +
          'width=(int)1920, height=(int)1080, ' +
          'format=(string)NV12, framerate=(fraction)30/1 ! ' +
          'nvvidconv flip-method=2 ! ' +
          'video/x-raw, width=(int){}, height=(int){}, ' +
          'format=(string)BGRx ! ' +
          'videoconvert ! appsink').format(width, height)

#cap = cv.VideoCapture(gst_str, cv.CAP_GSTREAMER)

def open_cam_usb(dev, width, height):
    # We want to set width and height here, otherwise we could just do:
    #     return cv2.VideoCapture(dev)
    gst_str = ("v4l2src device={} ! "
               "video/x-raw, width=(int){}, height=(int){}, format=(string)RGB ! "
               "videoconvert ! appsink").format(dev, width, height)
    return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

def open_cam_usb(dev):
    # We want to set width and height here, otherwise we could just do:
    #     return cv2.VideoCapture(dev)
    gst_str = ("v4l2src device=/dev/video{} ! "
	       "image/jpeg, format=(string)RGGB ! "
	       " jpegdec ! videoconvert ! queue ! appsink").format(dev)
    return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)



def start_cycle(config):


    use_gstream = False
    serial_port = config['serial_port']
    user_id = config['user_id']
    runner = RunnerApp(serial_port, user_id)

    runner.fetchConfiguration()
    runner.fetchRegisteredTeams()

    action = -1

    device = 0
    team_label_id = None
    session_mode = None
    battle_style = None


    for key in config:
        val = config[key]
        if val is None:
            continue
        if key == 'device':
            device = config[key]
        if key == 'team_label_id':
            team_label_id = config[key]
        if key == 'ai_style':
            runner.aiStyle = config[key]
        if key == 'session_mode':
            session_mode = config[key]
        if key == 'battle_style':
            battle_style = config[key]
        if key == 'trainer_name':
            runner.trainerName = config[key]
        if key == 'new_team_name':
            runner.newTeamName = config[key]

    if battle_style == 'wild':
        runner.matchStyle = "Wild Match"
        runner.matchStyleIndex = 1
    elif battle_style == 'network':
        runner.matchStyle = "Network Match"
        runner.matchStyleIndex = 0

    if team_label_id is not None:
        # ensure team exists
        for idx, team in enumerate(runner.registeredTeamItems):
            if team_label_id == team['team_label_id']:
                runner.registeredTeamId = team_label_id
                runner.registeredTeamIndex = idx + 1

    if session_mode == 'single':
        runner.createNewSession()
    elif session_mode == 'continuous':
        runner.oneTimeSetupCreateSilentNetworkSession()

#    cam = cv2.VideoCapture("/dev/video2")
#    cam = open_cam_usb("2")
    if use_gstream:
        cam = open_cam_usb(device)
    else:
        cam = cv2.VideoCapture(device)
#    cam.set(cv2.CAP_FFMPEG,True)
#    cam.set(cv2.CAP_PROP_FPS,30)
#    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
#    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1);

    i = 0
    actionCoolDown = time.time()
    wait_threshold = 0.2
    action = None

    while(runner.runSession or runner.inContinuousOnlineBattle):

        cam.grab()
        success, image = cam.read()
        height , width , layers =  image.shape
        new_h=720
        new_w=1280
        imageSrc = cv2.resize(image, (new_w, new_h))

        if runner.performingNetworkRequest == False:
            if wait_threshold is None:
                wait_threshold = runner.wait
                actionCoolDown = time.time()

            if time.time() - actionCoolDown >= wait_threshold and not runner.waitingForAction:
                runner.performingNetworkRequest = True
                runner.capture(imageSrc)
                wait_threshold = None

        else:
#            cam.grab()
            pass

    runner.fetchRegisteredTeams()
    runner.disconnectFromTwitch()

    cam.release()
#    _out.release()
    cv2.destroyAllWindows()




def main(argv):
    useConfig = False
    config = DEFAULT_CONFIG
    try:
        opts, args = getopt.getopt(argv,"hi")
    except getopt.GetoptError:
        printError( 'Invalid arguments' )
    for opt, arg in opts:
        if opt == '-h':
            print('use a config file')
            sys.exit(0)
        elif opt == '-i':
            useConfig = True

    if useConfig:
        inJson = args[0]
        print(args)
        with open(inJson, "r") as read_file:
            config = json.load(read_file)

    start_cycle(config)



if __name__ == "__main__":
    main(sys.argv[1:])

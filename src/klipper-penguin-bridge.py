import time
import schedule
import json
import requests
import subprocess
import logging

VERSION = "0.1b-20211012"
CONFIG_FILE = "./config.json"
LOG_LEVEL = logging.ERROR
LOG_FILE = "/var/log/klipper-penguin-bridge.log"
#LOG_FILE = "./klipper-penguin-bridge.log"


class SystemConfig(object):

    def __init__(self, configFile):
        configJson = {}
        with open(configFile) as config_file:
            configJson = json.loads(config_file.read())
        # check app config
        if "moonrakerHost" not in configJson or "moonrakerPort" not in configJson or "updateInterval" not in configJson or "taskList" not in configJson or "apiTimeout" not in configJson:
            raise ValueError("Missing config parameter(s)")
        if type(configJson["moonrakerHost"]) != str or configJson["moonrakerHost"] == "":
            raise ValueError("Invalid moonrakerHost")
        if type(configJson["moonrakerPort"]) != int or configJson["moonrakerPort"] <= 0:
            raise ValueError("Invalid moonrakerPort")
        if type(configJson["apiTimeout"]) != int or configJson["apiTimeout"] <= 0:
            raise ValueError("Invalid apiTimeout")
        if type(configJson["updateInterval"]) != int or configJson["updateInterval"] <= 0:
            raise ValueError("Invalid updateInterval")
        if type(configJson["taskList"]) != list or len(configJson["taskList"]) <= 0:
            raise ValueError("Invalid taskList")
        
        self.moonrakerHost = configJson["moonrakerHost"]
        self.moonrakerPort = configJson["moonrakerPort"]
        self.apiTimeout = configJson["apiTimeout"]
        self.updateInterval = configJson["updateInterval"]
        self.taskList = []

        # parse task config
        for rawTask in configJson["taskList"]:
            tmpTask = Task(rawTask)
            self.taskList.append(tmpTask)


class Task(object):
    def __init__(self, rawObj):
        if "command" not in rawObj or "execTimeout" not in rawObj or "variableName" not in rawObj or "isNumber" not in rawObj:
            raise ValueError("Missing parameter(s)")
        if type(rawObj["command"]) != str or rawObj["command"] == "":
            raise ValueError("Invalid command")
        if type(rawObj["variableName"]) != str or rawObj["variableName"] == "":
            raise ValueError("Invalid variableName")
        if type(rawObj["execTimeout"]) != int or rawObj["execTimeout"] <= 0:
            raise ValueError("Invalid execTimeout")
        if not isinstance(rawObj["isNumber"], bool):
            raise ValueError("Invalid isNumber")

        self.command = rawObj["command"]
        self.execTimeout = rawObj["execTimeout"]
        self.variableName = rawObj["variableName"]
        self.isNumber = rawObj["isNumber"]

class TaskRunner(object):
    def __init__(self, config):
        self.config = config

    def _getExecResult(self, command, cwd=None, timeout=1):
        logging.debug("#EXEC : " + command)
        proc = subprocess.Popen([command], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout = ""
        stderr = ""
        try:
            (stdout, stderr) = proc.communicate(timeout=timeout)
            logging.debug("StdOut" + str(stdout))
            logging.debug("StdErr" + str(stderr))
        except Exception as e:
            logging.error("Exception" + str(e))
            logging.error("Error" + str(stderr))
            return "none"

        resultStr = stdout.decode('utf-8').replace("\n", "")
        if resultStr == "":
            return "none"

        return resultStr

    def _updateVarValue(self, varName, isNumber, varValue):

        postData = ""
        if isNumber:
            postData = {"commands": ["SET_GCODE_VARIABLE MACRO=KLIPPER_PENGUIN_BRIDGE VARIABLE=" + varName + " VALUE=" + varValue ]}
        else:
            postData = {"commands": ["SET_GCODE_VARIABLE MACRO=KLIPPER_PENGUIN_BRIDGE VARIABLE=" + varName + " VALUE=\'\"" + varValue + "\"\'"]}

        url = "http://" + self.config.moonrakerHost + ":" + str(self.config.moonrakerPort) + "/api/printer/command"

        try:
            rawResult = requests.post(url, data=str(json.dumps(postData)), headers={
                                      'Content-type': 'application/json', 'Accept': 'application/json'}, timeout=self.config.apiTimeout)
            if rawResult.status_code in range(200, 300):
                return True
        except Exception as e:
            logging.error("exception" + str(e))
            return False
        return False

    def _getCurrentVariableState(self):
        try:
            queryUrl = "http://" + self.config.moonrakerHost + ":" + str(self.config.moonrakerPort) + "/printer/objects/query?gcode_macro KLIPPER_PENGUIN_BRIDGE"
            rawResult = requests.get(queryUrl, timeout = self.config.apiTimeout)
            if rawResult.status_code in range(200, 300):
                return rawResult.json()["result"]["status"]["gcode_macro KLIPPER_PENGUIN_BRIDGE"]
            else:
                logging.error("Failed to get current variable state")
                return None
        except Exception as e:
            logging.error("exception" + str(e))
            return None

    def _needUpdate(self,resultValue, variableName, isNumber,currentState):
        if currentState == None:
            return False

        try:
            if isNumber:
                return float(resultValue) != currentState[variableName]
            else:
                return resultValue != currentState[variableName]
        except Exception as e:
            logging.error("Exception" + str(e))
            return False


    def run(self):
        logging.info("# Running task route...")
        currentState = self._getCurrentVariableState()
        for task in self.config.taskList:
            logging.info("\t" + "# Exec command for " + task.variableName + " variable")
            resultStr = self._getExecResult(command=task.command, timeout=task.execTimeout)
            logging.info("\t" + "RESULT : " + resultStr)
            if self._needUpdate(resultStr, task.variableName, task.isNumber, currentState):
                if self._updateVarValue(task.variableName,task.isNumber, resultStr):
                    logging.info("\t" + "Api update success")
                else:
                    logging.info("\t" + "Api update failed")
            else:
                logging.info("\t" + "Skip api update")


def main():
    # init log
    logging.basicConfig(level=LOG_LEVEL,  handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()], format="%(asctime)-15s %(levelname)-8s %(message)s")
    # read config file
    config = SystemConfig(CONFIG_FILE)
    # init and run the task runer for the first time
    runner = TaskRunner(config)
    runner.run()
    # run task route each n second(s)
    schedule.every(config.updateInterval).seconds.do(runner.run)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()

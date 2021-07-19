import platform
import json
import threading
import time
from pycomm3.exceptions import CommError
import requests 
from requests.exceptions import Timeout
import os
from ftplib import FTP
import shutil
import psutil

# Overall Configuration Class to import that has 
# auxillary functions necesaary for the cloud
class Config:
    def __init__(self, *, ConfigFile=''):
        self.PLCIPAddress = ''
        self.AuditTrail = False
        self.Tags = []
        self.ServerURL = ''
        self.CloudWatchdogTime = 10
        self.CloudWatchdogValue = 0
        self.FTPTimerPreset = 120
        self.SMINumber = ''
        self.CPUPercent = 0.0
        self._ConnTestAppKey = ''
        self._CPURunning = False
        self._PanelviewIPAddress = ''
        self._FTPRunning = False
        self._LastFTPUpdate = 0
        self._CloudWatchdogRunning = False
        self._AppKey = ''
        self._FileRepo = ''
        self._AuditTrailStream = ''
        self._CloudWatchdogSession = requests.Session()
        self._LastWatchdogUpdate = 0
        self._OS = platform.system()
        self.LoadConfig(ConfigFile=ConfigFile)
        self._CloudWatchdogHeaders = {
            'Connection': 'keep-alive',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'appKey': self._ConnTestAppKey

        }
        

    # Read in configuration file and set values on object
    def LoadConfig(self, *, ConfigFile):
        with open(ConfigFile) as file:
            self._configData = json.load(file)
        self.PLCIPAddress = self._configData['Config']['PLCIPAddress']
        self.AuditTrail = self._configData['Config']['AuditTrail']
        self.ServerURL = self._configData['Config']['ServerURL']
        self.SMINumber = self._configData['Config']['SMINumber']
        self._FileRepo = self._configData['Config']['FileRepository']
        self._PanelviewIPAddress = self._configData['Config']['PanelviewIPAddress']
        self._AppKey = self._configData['Config']['AppKey']
        self._AuditTrailStream = self._configData['Config']['AuditTrailStream']
        self._ConnTestAppKey = self._configData['Config']['ConnTestAppKey']
        self.Tags = self._configData['Tags']
        return self._configData

    # Get specific tag value from globally returned tag list from PLC through pycomm3
    def GetTagValue(self, *, TagData=[], TagName=''):
        if TagData and TagName:
            result = [item.value for item in TagData if item[0] == TagName]
            return result[0]
        else:
            return None

    # Simpe function to get current time in milliseconds. Useful for time comparisons
    # ex.  startTime = ObjectName.GetTimeMS()
    #      endTime = ObjectName.GetTimeMS()
    #      totalTimeDifferenceInMilliseconds = (endTime - startTime)
    def GetTimeMS(self,):
        return round(time.time() * 1000)


    # Wrapper to call Thingworx watchdog function on a time basis
    # Wrapper starts function in seperate thread as to not block PLC comms
    def CloudWatchdog(self):
        timerPreset = self.CloudWatchdogTime * 1000
        if (((self.GetTimeMS() - self._LastWatchdogUpdate) >= timerPreset) and not self._CloudWatchdogRunning):
            self._CloudWatchdogRunning = True
            threading.Thread(target=self._CloudWatchdog).start()

    # Run RESTApi POST service to get current server time seconds
    # Using number value more accurate than just boolean on/off
    def _CloudWatchdog(self,):
        url = self.ServerURL + 'Things/Connection_Test/Services/ConnectionTest'
        try:
            serviceResult = self._CloudWatchdogSession.post(url, headers=self._CloudWatchdogHeaders)
            if serviceResult.status_code == 200:
                self.CloudWatchdogValue = (serviceResult.json())['rows'][0]['result']
                self._LastWatchdogUpdate = self.GetTimeMS()
            else:
                self.CloudWatchdogValue = 0
        except ConnectionError:
            self.CloudWatchdogValue = 0
        except ConnectionRefusedError:
            self.CloudWatchdogValue = 0
        except Timeout:
            self.CloudWatchdogValue = 0
        # Release Bit so watchdog can run again
        self._CloudWatchdogRunning = False


    # Wrapper to call FTP function on a time basis
    # Wrapper starts function in seperate thread as to not block PLC comms
    def AuditTrailFTP(self,):
        timerPreset = self.FTPTimerPreset * 1000

        if (((self.GetTimeMS() - self._LastFTPUpdate) >= timerPreset) and not self._FTPRunning):
            self._FTPRunning = True
            self._LastFTPUpdate = self.GetTimeMS()
            threading.Thread(target=self._AuditTrailFTP).start()

    # Audit Trail Create Directories (if they don't exists)
    # FTP audit trail csv files from Panelview
    # Delete file from Panelview as space is extremely limited
    def _AuditTrailFTP(self,):
        archiveDirectory = 'AuditTrailArchives'
        ftpDirectory = 'AuditTrail'
        directories = [archiveDirectory, ftpDirectory]
        # Try to create directories, if they exists move on
        for directory in directories:
            try:
                os.mkdir(directory)
            except: 
                pass  
        try: # FTP panelview, copy files over, then delete files from panelview
            ftp = FTP(self._PanelviewIPAddress, 'sanimatic', 'Tunn3lwa5h')
            for fileName in ftp.nlst():
                newFile = ftpDirectory + '/' + fileName
                with open(newFile, 'wb') as fileHandle:
                    ftp.retrbinary('RETR %s' % fileName, fileHandle.write)
                ftp.delete(fileName)
            ftp.quit()
        except:
            pass
        self._AuditTrailUpload()
        self._FTPRunning = False
        
        
    # Wrapper to call Audit Trail Upload in 
    # seperate thread as to not block PLC comms
    def _AuditTrailUpload(self,):
        auditTrailDirectory = 'AuditTrail'
        fileList = [file for file in os.listdir(auditTrailDirectory) if os.path.isfile(os.path.join(auditTrailDirectory, file))]
        for file in fileList:
            threading.Thread(target=self._AuditTrailUploadFile, args=(file,)).start()

    def _AuditTrailUploadFile(self, file):
        auditTrail = ''
        auditTrailDirectory = 'AuditTrail'
        auditTrailArchives = 'AuditTrailArchives'
        fileName = auditTrailDirectory + '\\' + file
        entityType = 'Things/'
        entity = 'SaniMatic.SaniTrendServices.AuditTrailServices/'
        entityAttributes = 'Services/'
        attributeName = 'UploadAuditTrail'
        url = (
            self.ServerURL + 
            entityType +
            entity + 
            entityAttributes + 
            attributeName
        )
        headers = {
            'Connection' : 'keep-alive',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'appKey': self._AppKey
        }
        try:
            with open(fileName, 'r', newline='') as CSVData:
                auditTrail = CSVData.read()

            payload = {
                'data': auditTrail,
                'FileRepo': self._FileRepo,
                'AuditTrail': self._AuditTrailStream,
                'Path': '/Audit_Trails/' + self.SMINumber + "/" + file    
            }

            session = requests.Session()
            result = session.post(url, headers=headers, json=payload)

            if result.status_code == 200:
                shutil.move(fileName, auditTrailArchives)

        except:
            print('FTP Upload Failed')
            pass


    # Wrapper to call CPU Usage 
    # seperate thread as to not block PLC comms
    def GetCPUUsage(self,):
        if not self._CPURunning:
            self._CPURunning = True
            threading.Thread(target=self._GetCPUUsage).start()

    def _GetCPUUsage(self,):
        self.CPUPercent = psutil.cpu_percent(2)
        self._CPURunning = False
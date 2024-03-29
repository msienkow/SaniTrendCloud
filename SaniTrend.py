import SaniTrendCloud
import time
import os
from datetime import datetime
from pycomm3 import LogixDriver
from pycomm3.exceptions import CommError
    
def main():

    # Set up SaniTrend parameters, tags, cloud configurations, etc...
    SaniTrend = SaniTrendCloud.Config(ConfigFile='SaniTrendConfig.json')

    # Setup PLC Communication Driver
    PLC = LogixDriver(SaniTrend.PLCIPAddress)

    PLCErrorCount = 0
    lastClockUpdate = 0
    runCode = True

    while runCode:
        try:
            # Get CPU Percentage
            SaniTrend.GetCPUUsage()

            # PLC, PC, and SaniTrend Cloud Watchdog
            SaniTrend.CloudWatchdog()

            # SaniTrend Cloud Audit Trail
            if SaniTrend.AuditTrail:
                SaniTrend.AuditTrailFTP()

            if PLC.connected:
                # Read PLC tags
                tagData = PLC.read(*SaniTrend.Tags)

                # Write tag data to PLC
                PLC.write(
                    (
                        'Program:SaniTrendCloud.STC_Server_Seconds', 
                        SaniTrend.CloudWatchdogValue
                    ),
                    (
                        'Program:SaniTrendCloud.STC_CPU_Usage', 
                        SaniTrend.CPUPercent
                    ),
                    (
                        'Program:SaniTrendCloud.STC_PC_IP_Address',
                        SaniTrend.PCIPAddress
                    ),
                    (
                        'Program:SaniTrendCloud.STC_SaniTrend_Watchdog',
                        SaniTrend.GetTagValue(
                            TagData=tagData, 
                            TagName='Program:SaniTrendCloud.STC_PLC_Watchdog'
                        )
                    )
                )

                # Update PLC Clock to PC time
                # currentMinute = datetime.now().minute
                # if currentMinute != lastClockUpdate:
                #     PLC.set_plc_time()
                #     lastClockUpdate = currentMinute
 
                # Check for reboot request
                reboot = SaniTrend.GetTagValue(TagData=tagData, TagName='Program:SaniTrendCloud.STC_Reboot_Command')
                if reboot:
                    runCode = False
                    PLC.write((
                        'Program:SaniTrendCloud.STC_Reboot_Response',
                        2
                    ))
                    PLC.close()
                    time.sleep(5) 
                    
                    if SaniTrend._OS == 'Windows':                
                        os.system('shutdown /r /t 1')

                # Reset PLC error count if everything succeeded
                PLCErrorCount = 0
                
            else:
                PLC.open()

            time.sleep(0.5)

        except CommError:
            PLCErrorCount += 1
            print(f'Communication Error! Fail Count: {PLCErrorCount}')
            SaniTrend.LogErrorToFile('PLC Comms Failed', CommError)
            if PLCErrorCount < 6:
                time.sleep(10)
            else:
                time.sleep(30)
            PLC = LogixDriver(SaniTrend.PLCIPAddress)

        except KeyboardInterrupt:
            print("\n\nExiting Python and closing PLC connection...\n\n\n")
            PLC.close()
            runCode = False
            
        except:
            print('Shutting Down...')
            PLC.close()
            runCode = False

if __name__ == "__main__":
    main()
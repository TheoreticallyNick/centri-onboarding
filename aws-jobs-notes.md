Steps to run a job on IoT device

## TODO ##
- Specify the jobs document standard
- Specify the clientToken standard

## Start of Jobs Process ##
This is the start of the Jobs process where we can send commands to the device from the cloud on an unsynchronized basis.

1. Job is uploaded with instruction json file with the associated <deviceID> of which devices receive the uploaded file.
    The job is now marked as "Queued" in the cloud. 
    A job file is a JSON file that doesn't require any specific format and can have custom value pairs that we define.
    For example, the JOB file can look like this: 
    {
        "operation": "customJob",
        "otherInfo": "someValue"
    }

2. Device connects to the broker

3. Publishes data to "logi2/device/<deviceID>"

### Option 1 -- GetPendingJobExecutions ### info: https://docs.aws.amazon.com/iot/latest/developerguide/jobs-mqtt-api.html#mqtt-getpendingjobexecutions
This is our first option to view the pending jobs in the cloud that the device needs to execute on.

4. Device subscribes to "$aws/things/<deviceID>/jobs/get/accepted" and "$aws/things/<deviceID>/jobs/get/rejected"

5. Device publishes message to "$aws/things/<deviceID>/jobs/get", the request should look like this: 
    { 
    "clientToken": "string" // Optional. A client token used to correlate requests and responses. Enter an arbitrary value here and it is reflected in the response.
    }

6. AWS IoT Core publishes job information to the topics "$aws/things/<deviceID>/jobs/get/accepted" and/or "$aws/things/<deviceID>/jobs/get/rejected"
    {
        "clientToken": "string", // A client token used to correlate requests and responses, will be the same as the client toke from the request.
        "timestamp": 1625328544, // The time, in seconds since the epoch, when the message was sent.
        "inProgressJobs": [], // A list of JobExecutionSummary objects with status IN_PROGRESS.
        "queuedJobs": [ // A list of JobExecutionSummary objects with status QUEUED.
            {
            "jobId": "test_job", // The unique identifier you assigned to this job when it was created.
            "queuedAt": 1625268804, // The time, in seconds since the epoch, when the job execution was enqueued.
            "lastUpdatedAt": 1625268804, // The time, in seconds since the epoch, when the job execution was last updated.
            "executionNumber": 1, // A number that identifies a job execution on a device.
            "versionNumber": 1 // The version of the job execution. Job execution versions are incremented each time the AWS IoT Jobs service receives an update from a device.
            }
        ]
    }

7. The device receives the payload from step 6 since it is subscribed to the "$aws/things/<deviceID>/jobs/get/accepted" and can view queued jobs and job information.
    From here, we can determine the <jobID> that we must reference in execution step

### Option 2 -- DescribeJobExecution ### info: https://docs.aws.amazon.com/iot/latest/developerguide/jobs-mqtt-api.html#mqtt-describejobexecution
This is our second option to view the pending jobs in the cloud that the device needs to execute on.
Unlike option 1, this option focuses only on the "next" job in the queue in FIFO operation (in order that the jobs were created)

4. Device subscribes to "$aws/things/<deviceID>/jobs/$next/get/accepted" and "$aws/things/<deviceID>/jobs/$next/get/rejected"

5. Device publishes to "$aws/things/<deviceID>/jobs/$next/get"
    { 
        "executionNumber": long, // Optional. A number that identifies a job execution on a device. If not specified, the latest job execution is returned.
        "includeJobDocument": boolean, // Optional. Unless set to false, the response contains the job document. The default is true.
        "clientToken": "string" // A client token used to correlate requests and responses. Enter an arbitrary value here and it is reflected in the response.
    }

6. AWS IoT Core publishes job information to the "$aws/things/<deviceID>/jobs/$next/get/accepted" and/or "$aws/things/<deviceID>/jobs/$next/get/rejected"
    {
        "clientToken": "string",
        "timestamp": 1625352024,
        "execution": {
            "jobId": "test_job2",
            "status": "QUEUED",
            "queuedAt": 1625351385,
            "lastUpdatedAt": 1625351385,
            "versionNumber": 1,
            "executionNumber": 1,
            "jobDocument": { // Job JSON Document from S3 bucket that was input during step 1
                "operation": "customJob",
                "otherInfo": "someValue"
            }
        }
    }

### StartNextPendingJobExecution ### info: https://docs.aws.amazon.com/iot/latest/developerguide/jobs-mqtt-api.html#mqtt-startnextpendingjobexecution
This step lets the cloud know that we are executing the job at the device level.

8. Device subscribes to $aws/things/<deviceID>/jobs/start-next/accepted

9. Device publishes message to $aws/things/<deviceID>/jobs/start-next
    { 
        "statusDetails": { // A collection of name-value pairs that describe the status of the job execution.
            "string": "job-execution-state"
            ...
        },
        "stepTimeoutInMinutes": long, // Specifies the amount of time this device has to finish execution of this job (in minutes).
        "clientToken": "string" // A client token used to correlate requests and responses. Enter an arbitrary value here and it is reflected in the response.
    }

10. AWS IoT Core publishes the following information to $aws/things/<deviceID>/jobs/start-next/accepted
    This information includes the information stored in the jobDocument which can include information about html link to updated software rev, 
    commands to reboot the device, etc.
    {
        "clientToken": "string",
        "timestamp": 1625329827,
        "execution": {
            "jobId": "test_job",
            "status": "IN_PROGRESS",
            "statusDetails": {
                "string": "job-execution-state"
            },
            "queuedAt": 1625268804,
            "startedAt": 1625329827,
            "lastUpdatedAt": 1625329827,
            "versionNumber": 2,
            "executionNumber": 1,
            "approximateSecondsBeforeTimedOut": 599,
            "jobDocument": {
                "operation": "customJob",
                "otherInfo": "someValue"
            }
        }
    }

11. The job is now in "IN_PROGRESS" stage for that specific device in the cloud

12. Device can now use instructions/commands from "jobDocument" section of the JSON file as inputs to commands on the device or for a link to a ota update.

### UpdateJobExecution ### info: https://docs.aws.amazon.com/iot/latest/developerguide/jobs-mqtt-api.html#mqtt-updatejobexecution
Once the job is completed on the device side, we must now confirm with the cloud that the device has completed the job.

13. Device subscribes to $aws/things/<deviceID>/jobs/<jobId>/update/accepted

14. Device publishes to $aws/things/<deviceID>/jobs/<jobId>/update
    {
        "status": "job-execution-state", // The new status for the job execution (IN_PROGRESS, FAILED, SUCCEEDED, or REJECTED). This must be specified on every update
        "statusDetails": {  // A collection of name-value pairs that describe the status of the job execution. If not specified, the statusDetails are unchanged.
            "string": "string"
            ...
        },
        "expectedVersion": "number", // The expected current version of the job execution. 
        "executionNumber": long, // Optional. A number that identifies a job execution on a device. If not specified, the latest job execution is used.
        "includeJobExecutionState": boolean, // Optional. When included and set to true, the response contains the JobExecutionState field. The default is false.
        "includeJobDocument": boolean,
        "stepTimeoutInMinutes": long,
        "clientToken": "string"
    }

15. AWS IoT Core publishes the timestamp of the update acceptance to $aws/things/<deviceID>/jobs/<jobId>/update/accepted

16. The job is now complete.

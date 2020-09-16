import boto3
import json
import random
import string
import os
import qrcode
from PIL import Image  
import PIL
import uuid

# The purpose of this script is to onboard devices during the manufacturing process. This involves:
# 1) Creating a "thing" in a AWS IoT
# 2) Creating certificates for the "thing" to allow TCP access to the MQTT broker
# 3) Updating the "thing" shadow
# 4) Updating the dynamoDB database for the new device

# TODO:
# 1) Upload the certs, id's, and keys to the device - need to automate Root-CA file
# 2) DONE - Run a test publish sequence with AWS
# 3) DONE - Print the label and place it on the device
# 4) DONE - Insert new entry in device table that links SIM, thingName, serial
# 5) DONE - Create device entry in DynamoDB device status series
# 6) DONE - Update the device shadow prior to updating the dynamodb table

# Variables that will be assigned during manufacturing

thingArn = ''
thingId = '' # Assigned by AWS as a v4 uuid
thingName = str(uuid.uuid4()).replace('-','') # thingName is going to be the last 12 digits of the uuid
thingType = 'LOGI-1' #thingType should be the model number (ie )
defaultPolicyName = 'default-logi-policy'
sim = '8944501705192074069'
serial = '1'
#thingGroup = 'Ford_Propane'
#thingGroupArn = 'arn:aws:iot:us-east-2:354778082397:thinggroup/Ford_Propane'

###################################################

def createThing():
    # 1. Creates a 'thing' in AWS with the properID and 
    global thingClient
    
    # 1a. Create a thing call to AWS using boto3 client
    thingResponse = thingClient.create_thing(thingName = thingName, thingTypeName = thingType)
    data = json.loads(json.dumps(thingResponse, sort_keys=False, indent=4))

    print(data)

    # 1b. 
    for element in data: 
        if element == 'thingArn':
            thingArn = data['thingArn']
        elif element == 'thingId':
            thingId = data['thingId']

    # 1c. Add newly created thing to appropriante thing group which corresponds to the customer
    #response = thingClient.add_thing_to_thing_group(thingName = thingName, thingArn = thingArn)

    # 1d. create a directly for thing keys which includes cert, private, and public keys
    os.mkdir('keys')

def createCertificate():
    # 2. creates certificate, private, and public key files for AWS interfacing
    global thingClient

    certResponse = thingClient.create_keys_and_certificate(setAsActive = True)
    data = json.loads(json.dumps(certResponse, sort_keys=False, indent=4))

    print(data)

    for element in data:
        if element == 'certificateArn':
            certificateArn = data['certificateArn']
        elif element == 'keyPair':
            PublicKey = data['keyPair']['PublicKey']
            PrivateKey = data['keyPair']['PrivateKey']
        elif element == 'certificatePem':
            certificatePem = data['certificatePem']
        elif element == 'certificateId':
            certificateId = data['certificateId']

    # 2c. create individual files in the keys directory
    with open('keys' + '/' + thingName + '.public.key', 'w') as outfile:
        outfile.write(PublicKey)
    with open('keys' + '/' + thingName + '.private.key', 'w') as outfile:
        outfile.write(PrivateKey)
    with open('keys' + '/' + thingName + '.cert.pem', 'w') as outfile:
        outfile.write(certificatePem)
    with open('keys' + '/' + 'thingName' + '.txt', 'w') as outfile:
        outfile.write(thingName)

    # 2d. create AWS policy for newly formed thing
    response = thingClient.attach_policy(policyName = defaultPolicyName, target = certificateArn)
    
    # 2e. attach policy to the newly formed thing
    response = thingClient.attach_thing_principal(thingName = thingName, principal = certificateArn)

def createQRcode():
    qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
    )
    qr.add_data(thingName)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    img.save('qrcode.png')

def updateDynamoDB():
    dynamo = boto3.resource('dynamodb', region_name='us-east-1')
    table1 = dynamo.Table('logi-status')
    table1.put_item(Item={'id': thingName, 'serial': serial, 'sim': sim})

def updateShadow():
    client_shadow = boto3.client('iot-data', region_name='us-east-1')
    shadow = {'state': {'reported': { 'id': thingName, 'serial': serial, 'sim': sim, 'user_id': 'null'}}}
    shadow_bytes = json.dumps(shadow).encode('utf-8')
    response = client_shadow.update_thing_shadow(thingName=thingName, shadowName='logi-1-shadow', payload=shadow_bytes)


thingClient = boto3.client('iot', region_name='us-east-1')
# 1. create thing in AWS
createThing()
# 2. create thing certificates
createCertificate()
# 3. generate QR code
createQRcode()
# 4. update device shadow
updateShadow()
# 5. update dynamoDB table
updateDynamoDB()



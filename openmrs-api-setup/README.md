# OpenMRS API Setup Verification
Author: Radhika Sharma

## Prerequisites
Before running the commands below, ensure the following are installed:

- Docker
- Docker Compose
- OpenMRS Docker environment

## Objective
Verify that the OpenMRS Reference Application runs locally and confirm that the REST API endpoints work correctly.

## Authentication
OpenMRS REST APIs use **Basic Authentication**.

Example credentials used locally:
Username: admin  
Password: Admin123

## Steps Performed

### 1. Start OpenMRS using Docker
docker compose up

The OpenMRS Reference Application was accessed locally at:

http://localhost/openmrs

The sandbox instance contains test patients and realistic medical records that can be used for API testing.

---

### 2. Fetch patient data (GET request)

Endpoint:
GET /openmrs/ws/rest/v1/patient

Example command:

curl -u admin:Admin123 "http://localhost/openmrs/ws/rest/v1/patient?q=Leo"

This verifies that patient records can be successfully retrieved from the OpenMRS system.

---

### 3. Retrieve encounter types (GET request)

Endpoint:
GET /openmrs/ws/rest/v1/encountertype

Example command:

curl -u admin:Admin123 "http://localhost/openmrs/ws/rest/v1/encountertype"

This was used to identify the UUID for the Consultation encounter type.

---

### 4. Create consultation encounter (POST request)

Endpoint:
POST /openmrs/ws/rest/v1/encounter

Example command:

curl -u admin:Admin123 -H "Content-Type: application/json" \
-d '{ 
  "patient":"893546fd-b898-4943-80de-4fee21f8369c",
  "encounterType":"dd528487-82a5-4082-9c72-ed246bd49591",
  "location":"2ef7caf2-affa-4003-8fe7-128db6ce31ee",
  "encounterDatetime":"2026-04-11T18:00:00.000+0000"
}' \
"http://localhost/openmrs/ws/rest/v1/encounter"

### JSON Payload Explanation
- patient → patient UUID
- encounterType → type of medical encounter
- location → location UUID
- encounterDatetime → date and time of the encounter

## Result
The OpenMRS Reference Application was successfully launched using Docker.

The following REST API operations were verified:
- Fetching patient records using GET
- Retrieving encounter types
- Creating a consultation encounter using POST

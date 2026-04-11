# OpenMRS API Setup Verification

Author: Radhika Sharma

## Prerequisites
Before running the commands below, ensure the following are installed:

- Docker
- Docker Compose
- OpenMRS Docker environment

## Objective
Verify that OpenMRS runs locally and that the REST API works.

## Steps Performed

### 1. Start OpenMRS using Docker
docker compose up

### 2. Query patient data
curl -u admin:Admin123 "http://localhost/openmrs/ws/rest/v1/patient?q=Leo"

### 3. Retrieve encounter types
curl -u admin:Admin123 "http://localhost/openmrs/ws/rest/v1/encountertype"

### 4. Create consultation encounter
curl -u admin:Admin123 -H "Content-Type: application/json" \
-d '{
"patient":"893546fd-b898-4943-80de-4fee21f8369c",
"encounterType":"dd528487-82a5-4082-9c72-ed246bd49591",
"location":"2ef7caf2-affa-4003-8fe7-128db6ce31ee",
"encounterDatetime":"2026-04-11T18:00:00.000+0000"
}' "http://localhost/openmrs/ws/rest/v1/encounter"

## Result
OpenMRS REST API was successfully verified locally.

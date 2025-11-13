# Deployment of OLDAP framework

The deployment of OLDAP framework relies on Ansible. The Dataflow is described as as follows

- **inventory.ini**  
  This file contains the variables that are dependent on where the Framework is being deployed.
- **oldap.env.j2**  
  This template defines how to render the environment variables for the OLDAP that are used be docker-compose.yml.
  The result is a .env file that is used by docker-compose.yml.
- **oldap.yml**  
  This file contains the Ansible playbook that deploys the OLDAP framework.
- **oldap-deploy.yml**
- **docker-compose.yml**
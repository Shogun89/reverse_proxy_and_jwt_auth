# Configuring a reverse proxy and adding authentication with nginx and FastAPI

# Intro
This is a continuation of the work I did in the previous [post](https://open.substack.com/pub/invariantsubspace/p/exploring-horizontal-scaling-with?r=4l2b0p&utm_campaign=post&utm_medium=web). While it is not necessary to understand the content of this post, I recommend reading it first. In the previous post I added a load balancer to the system, added database shards and read replicas to improve the system's performance. In this post I will update the load balancer to use nginx as a reverse proxy, add authentication to the system using FastAPI and modify the backend to use asynchronous code.

In line with our goal of building a robust, scalable system, this post will focus on three critical aspects of modern web architecture: authentication, reverse proxies, and asynchronous programming. As our application grows, we need to ensure secure access control while efficiently routing traffic between services. A well-designed authentication system protects our resources from unauthorized access, while a reverse proxy helps manage traffic, improve security, and enable seamless horizontal scaling. Additionally, by leveraging asynchronous programming patterns in FastAPI, we can handle concurrent requests more efficiently and improve our application's overall performance. We'll explore how to implement these components using nginx and FastAPI to create a high-performance, production-ready architecture.

In this post I will cover the following topics:

1. Reverse proxy : We'll explore how to configure nginx as a reverse proxy to improve the system's performance and security.
2. Authentication : We'll add an authentication layer to the system using FastAPI.
3. Asynchronous programming : We'll modify the backend to use asynchronous code to improve the system's performance.

We'll take the existing system as a starting point and modify it to add the new components. I've also done a significant refactor of the code to make it more modular and easier to understand. You can find the code for the existing system [here](https://github.com/Shogun89/horizontal_scaling) and the code for the new system [here](https://github.com/Shogun89/reverse_proxy_and_jwt_auth). I've decided not to use the same repository for the new system to avoid any issues with references the old code in previous posts. Another major change is the modularization of the code, which I'll cover in more detail later. 

Before we begin, I'm going to note that this post is not meant to be a comprehensive guide on any of the topics I'm covering. It is meant to be a practical guide on how to implement authentication, reverse proxies and asynchronous programming in a real-world scenario. In some areas I've made simplifications that may not be practical for a real-world application. This is after all (as before) a fictional e-commerce site.

In contrast to the previous post the features I'm covering here are fully implemented however there is still a lot of room for improvement. With that in mind I've added a markdown called future_work.md which contains a list of features that I'm hoping to cover in future posts however I have not yet implemented them. I'm not entirely sure how many posts this will take or the exact order and frequency of the posts however I'm hoping to cover all of the features in the future_work.md file.

# Systems architecture
Before we begin, I'll quickly go over the current system architecture and compare it with the previous architecture to understand the changes. Usually when I begin these projects I have a rough idea of the architecture I want to use however as I begin to implement the code I realize that I need to make changes. In this case I originally planned on just fixing the issues with the round robin load balancer however I realized that it made more sense to put it in front as a reverse proxy.

Below is a diagram of the current system architecture.

![Current system architecture](./images/architecture_diagram_current.png)

To illustrate the changes I'll also include a diagram of the previous system architecture.

![Previous system architecture](./images/architecture_diagram_previous.png)

The core change is the addition of the authentication layer and the reverse proxy. Previously we nginx set up to route traffic to the backend as a load balancer however this created a problem with the way it was configured. The nginx configuration used the default round robin algorithm to route traffic to the backend. The problem with this is that if the first request created a new user in one shard it would be routed to the same shard for all subsequent requests. This means that the user would not be created in the other shards and the user would not be able to access their account. 

Instead now we use nginx as a reverse proxy to route traffic to the backend and to the authentication service. Now someone can register an account and then we can use nginx to route them to the correct shard in a deterministic way. More specifically we route the user based on the modulo of the user id. Even user ids go to shard A and odd user ids go to shard B. In addition now in order to access any of the endpoints in the backend the user needs to be authenticated. In order to do this we use the authentication service with FastAPI and after registering a user they "login" which generates a JWT token. This token is then used to authenticate the user for the backend requests. Whenever you create a curl request to the backend via nginx it will trigger a request to the authentication service to validate the JWT token. If the token is valid then nginx will forward the request to the backend otherwise it will return a 401 Unauthorized error.

# Modularization & Structure
Before beginning to discuss the new features I'll quickly go over the new structure of the code and how I've tried to modularize it. Previously I had a project tree structure like this:
```
project_root/
├── backend/
├── images/
└── scripts/
```
and while this worked for a small project it has quickly become unwieldy as the project has grown. Now the project has the following structure:
```
project_root/
├── backend/
├── auth/
├── images/
├── router/
└── tests/
├── docs/
``` 

In addition to this I've also modularized the docker compose file based upon the services. This allows us to more easily manage the different services and their dependencies. Instead of all the services being defined one Docker Compose file I've created a separate file for each service. This makes it easier to understand and modify the different services and their dependencies. It also makes it easier to test them in isolation. The docker compose file for the current system can be found [here](./docker-compose.yml). This was made possible using the Docker extends feature which allows us to extend the configuration of a service from another file. At this point there are 9 or 10 services (if you include the tests) so it makes sense to modularize it this way.

# Reverse proxy
Most of the time I spent on this project was spent on the reverse proxy. In the previous post I did not go over the details of the nginx configuration. This post will cover the details of the nginx configuration and the different configurations I've tried. Nginx is a web server that can be used as a reverse proxy, load balancer, and HTTP cache. It is a powerful tool that can be used to improve the performance and security of the system. In this case we are using it as a reverse proxy to route traffic to the backend and the authentication service. Reverse proxy is just a fancy way of saying that nginx sits between the client and the backend and forwards the requests to the correct service. 

Nginx is configured using a .conf file. You can find a more detailed explanation of the different directives in the [official documentation](https://nginx.org/en/docs/). I will briefly go over some of the important parts of the configuration file.

## Maps
A map in nginx is a way to create a variable based on the value of another variable. There are two main maps I've added. The first is used to extract the JWT token from the authorization header. The second is used to route the user to the correct shard based on their user id which is embedded in the JWT token.

## Server block
The server block is used to configure the server itself. In this case we are using it to route traffic to the correct service. In particular the port is set to 80 which is the default port for HTTP. The server block also contains the location blocks which are used to route traffic to the correct service. There are three location blocks in total. The first is used to route traffic to the authentication service. The second is used to route traffic to the backend service. The third is used to validate the JWT token by passing the token to the authentication token verification endpoint.

The core idea here is simple: nginx acts as a gatekeeper between clients and our backend services. In a production environment, clients (like web browsers or mobile apps) would only interact with nginx, which then intelligently routes their requests to the appropriate internal service.

While our development environment (using Docker Compose) allows direct access to the FastAPI and authentication services for testing purposes, in a real production setup these services would be isolated within a private network. Only nginx would be exposed to the public internet, providing an additional layer of security and control.

# Authentication
The next part of the project is to add the authentication service. This service will primarily be responsible for registering users, logging in users, generating JWT tokens, and verifying JWT tokens. In addition it will also be responsible for changing passwords and updating user information. The basic idea is that we want to create a new user, login to get a JWT token, and then use that token to authenticate the user for the backend requests. A JWT token is a JSON Web Token which is a standard way of representing claims securely between two parties. 

Let's walk through an example of how this works in our system:

1. A user registers an account with the authentication service.
When they register an account they are assigned a user id using a column in the database which auto increments. 
To do this they call the auth/register endpoint like below
```bash
curl -X POST http://auth:8000/auth/register -H "Content-Type: application/json" -d '{"email": "user@test.com", "password": "Test89!"}'
```
There are several checks that are made against the email and password first in order to make sure that the user is registering does not already exist and that the password is strong. If these checks pass then the user is registered. 

2. When a user logs in they receive a JWT token.
The user then calls the auth/token endpoint to generate a JWT token in order to authenticate their requests to the backend.
```bash
curl -X POST http://auth:8000/auth/token -H "Content-Type: application/x-www-form-urlencoded" -d 'username=user@test.com&password=Test89!'
```
This will first check that the email and password are correct. If they are then it will generate a JWT token and return it to the user.

3. The auth token endpoint returns a JWT token.
I think it's important to cover exactly what this token is and what it contains. The token is a JSON Web Token which is a standard way of representing claims securely between two parties. If you look at the login_for_access_token function in the auth/api.py file you can see it will call the create_access_token function which will create the token based on the user's email and user id. The token will contain the user's email, user id, and an expiration time.
```python
    access_token = create_access_token(
        data={"sub": user.email},
        user_id=user.id
    )
```
If we look at the create_access_token function we can see it will create the token using the jwt.encode function. The token will be encoded using the SECRET_KEY and the ALGORITHM which are stored in the .env file. The token will have the following structure:
```
{
    "sub": "user@test.com",
    "user_id": 1
}
```
This is finally returned to the user who can then use it to authenticate their requests to the backend. For the purposes of this example the expiration time isn't used to encode the token however it can be used to control the lifespan of the token. 

```python
SECRET_KEY = "your-secret-key-here"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def create_access_token(data: dict, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        user_id: User ID to include in token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token as string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "user_id": user_id
    })
    
    # Create token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```
So if we were using the example above the token would be encoded using the SECRET_KEY and the ALGORITHM and would have the following structure:
```
{
    "sub": "user@test.com",
    "user_id": 1
}
```
Then this would produce the following token:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQHRlc3QuY29tIiwiZXhwIjoxNzMyNDgyMTM2LCJ1c2VyX2lkIjoxfQ.WyrgKiYB_HraBcyUiaZi-OEsux3JDBlpL7bzpETgiYE
```
For more information on JWT tokens you can read more [here](https://jwt.io/). In addition you can run the example_jwt_token.py file to see how the token is created.
4. The user makes a request to the backend.
The final part of the process is that the user makes a request to the backend. In order to do this they need to pass the JWT token in the authorization header. The header should have the following format:
```
Authorization: Bearer <JWT token>
```
This will then trigger a request to the authentication service to validate the JWT token. If the token is valid then nginx will forward the request to the backend otherwise it will return a 401 Unauthorized error. You can see that the _validate_token location block is configured to do just this by passing the token to the auth/verify endpoint. 

# Asynchronous programming
The final part of the project is to modify the backend to use asynchronous programming. This requires modifying a few things in each of the FastAPI servers (backend and authentication). I'll go over the changes I've made in more detail below.

* In each of the crud and api files we add the async keyword to the function definitions.
* For operation that have IO we add await in front of the function call.
* Instead of the regular SQLAlchemy sessionmaker we use the async version aiomysql.

For instance in our original backend api.py file we had the following code:
```python
@router.post("/users/{user_id}/orders", response_model=schemas.Order)
def create_order(user_id: int, db: Session = Depends(get_db)):
    return crud.create_order(db, user_id)
```
This is used to create a new order for a user. The Depends(get_db) is a dependency that will automatically call the get_db function and pass the session to the function. In the async version we have to do the following:

```python
@router.post("/orders", response_model=Order)
async def create_order(
    order: OrderCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new order."""
    return await crud.create_order(db, order)

```

The core idea here is that our fictional e-commerce site is receiving a lot of traffic and we want to make sure that we can handle it. By using asynchronous programming we can handle more requests per second. In addition we can also use the CPU more efficiently by doing other things while we are waiting for a request. Without this the system would have to wait for each request to finish before it could move on to the next one. This would make the system much slower and less efficient. 

# Testing
For the final part of the project I've added a simple script to test the additional authentication and reverse proxy features. I haven't added any tests for the asynchronous programming yet but I will in a future post. In a future post I intend to look at how the system handles load with the asynchronous backend using Grafana and Prometheus.

The script will do the following:
* Register a new user
* Login to get a JWT token
* Use the JWT token to access the backend

We then will validate the backend requests by checking the database and looking at the logs. The script can be found [here](./tests/simple_register_test.py). This script is not meant to be a comprehensive test of the system but rather a simple way to validate that the new features are working. In a future post I'll talk about unit and integration testing to cover more of the system. 

In order to run all of this you will first have to run the docker compose file. You can do this by running the following command in the project root:
```bash
docker compose up --build -d
```
This will build the images and start the containers in detached mode. Once everything is built and started you can run the script. This could take a few minutes to download the dependencies and build the project. In addition it will take a bit of time for the databases and everything to be be ready. Note that in the backend entrypoint (api_entrypoint.sh) file is probably the main bottleneck. It looks like this:

```bash
#!/bin/bash

# Source the helper scripts
source scripts/wait_for_mysql.sh
source scripts/enable_mysql_replication.sh

echo "Starting database initialization..."
echo "Environment variables:"
echo "SHARD: $SHARD"
echo "DB_HOST: $DB_HOST"
echo "DB_NAME: $DB_NAME"
echo "DB_USER: $DB_USER"

# Wait for MySQL master with increased timeout
wait_for_mysql "mysql-master-$SHARD" 3306 60

# Wait a bit more to ensure MySQL is fully ready
sleep 5

# Initialize the database first
python init_db.py

# Verify tables were created
mysql -h mysql-master-$SHARD -u root -prootpassword fastapi_db -e "SHOW TABLES;"

# Then setup replication for this shard
setup_replication "mysql-master-$SHARD" "mysql-replica-$SHARD"

# Start the application
uvicorn main:app --host 0.0.0.0 --port 8000
```
This waits for the MySQL server to be ready and then initializes the database, turns on replication, initializes the database and starts the backend FastAPI servers. There is a similar entrypoint for the authentication service but it is much simpler.

## Simple registration test
The simple registration test is used to test the registration and login process. It is not meant to be a comprehensive test of the system but rather a simple way to validate that the new features are working. You can find the script [here](./tests/simple_register_test.py).

I've attached some logs of the test passing below:
```
C:\Users\ryhow\Documents\python\substack\async\replicas\tests>python simple_register_test.py
Starting test...
Test credentials generated
Email:  test_ftpu10h7sp@example.com
Password:  Pp8!xKvL%Sg568
Testing user registration...

Status Code: 200
Response: {
  "email": "test_ftpu10h7sp@example.com",
  "is_active": true,
  "is_admin": false,
  "id": 2,
  "created_at": "2024-11-25T23:24:34",
  "last_login": null
}

Getting token for user: test_ftpu10h7sp@example.com
Token obtained successfully

Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2Z0cHUxMGg3c3BAZXhhbXBsZS5jb20iLCJleHAiOjE3MzI1Nzg4NzUsInVzZXJfaWQiOjJ9.wz5TJKsqRSQpoMxqT6SQpmtCZflm3W6NzGd2FUN5zhk

Testing backend with token for user: test_ftpu10h7sp@example.com
Making request to: http://localhost:80/backend/api/users
Headers: {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2Z0cHUxMGg3c3BAZXhhbXBsZS5jb20iLCJleHAiOjE3MzI1Nzg4NzUsInVzZXJfaWQiOjJ9.wz5TJKsqRSQpoMxqT6SQpmtCZflm3W6NzGd2FUN5zhk', 'Content-Type': 'application/json'}
User creation status code: 200
Response headers: {'Server': 'nginx/1.27.2', 'Date': 'Mon, 25 Nov 2024 23:24:35 GMT', 'Content-Type': 'application/json', 'Content-Length': '116', 'Connection': 'keep-alive', 'X-Debug-Backend-Server': 'api-a:8000', 'X-Debug-Original-URI': '/backend/api/users', 'X-Debug-URI': '/api/users'}
Response: {
  "email": "test_ftpu10h7sp@example.com",
  "is_active": true,
  "id": 1,
  "created_at": "2024-11-25T23:24:35",
  "last_login": null
}
Backend test completed
```

Now we can see that the user was created successfully and the backend request was successful but we should double check a few things to make sure everything is working correctly. First we can see it went to api-a and not api-b. We can also see that the original URI was /backend/api/users and the URI after the rewrite was /api/users. This confirms that the rewrite is working as expected. We will check the auth db to make sure the user was created and then we'll compare to the nginx routing logic.

```bash
docker exec -it auth-db mysql -uroot -prootpassword -e "use auth_db; select * from auth_users;"
```
and I see the following:
```
mysql: [Warning] Using a password on the command line interface can be insecure.
+----+-----------------------------+--------------------------------------------------------------+-----------+----------+------------------------------------------------+-----------+----------+---------------------+---------------------+
|  1 | test_y9y1x1hyz7@example.com | $2b$12$sLdVhy/vfRc7yM0iQZYC4edc6f8vzDBoONYZ80zxgREOO4ZhnjDF2 |         1 |        0 | 2024-11-25 23:22:57 | 2024-11-25 23:22:58 |
|  2 | test_ftpu10h7sp@example.com | $2b$12$K7Vc6UgjrvqiBjuH7m.RXeOv.UxZ6BRlXXFDUbcLIbhGI/6oLcQXu |         1 |        0 | 2024-11-25 23:24:34 | 2024-11-25 23:24:35 |
+----+-----------------------------+--------------------------------------------------------------+-----------+----------+---------------------+---------------------+
```
So the user_id is 2 which is odd so it does go to the second backend. Now checking the nginx config we see
```
    # Shard routing based on user_id
    map $user_id $backend_server {
        "~^[13579]" "api-b:8000";  # Odd IDs go to shard B
        default "api-a:8000";       # Even IDs go to shard A
    }
```

So this is correct and the user was routed to the correct backend. I'll note that I ran this test a second time after an error so it should in general actually route to api-b since user id 1 is odd. 


# Conclusion    
We've now added a reverse proxy, authentication service, and modified the backend to use asynchronous programming. This is a significant improvement to the system and lays a good foundation for future growth. In the next post we'll look at how to monitor the system using Prometheus and Grafana. 

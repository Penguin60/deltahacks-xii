import redis

def reset_demo_data():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.flushall()
    print("demo cleared")

if __name__ == "main":
    reset_demo_data()

tasks = []

@app.post("/task")
def x(a: dict):
    a["id"] = len(tasks)
    tasks.append(a)
    return a

@app.get("/tasks")
def z():
    return tasks

@app.put("/task/{id}")
def y(id: int, body: dict):
    for i in tasks:
        if i["id"] == id:
            i.update(body)
            return i

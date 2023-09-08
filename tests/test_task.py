from nodeorc import log

def test_velocity_flow(task, temp_path):
    task.execute(temp_path)



def test_velocity_flow_local(task_local, temp_path):
    task_local.execute(temp_path)

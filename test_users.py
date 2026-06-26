import sys, json, subprocess
r = subprocess.run(['curl.exe', '-s', '-X', 'POST', 'http://localhost:8000/auth/login',
    '-H', 'Content-Type: application/json',
    '-d', '{"email":"superadmin@zoiko.com","password":"admin123"}'],
    capture_output=True, text=True)
t = json.loads(r.stdout)['access_token']
headers = ['Authorization: Bearer ' + t]

# Invite user
r = subprocess.run(['curl.exe', '-s', '-X', 'POST', 'http://localhost:8000/super-admin/users/invite',
    '-H', 'Content-Type: application/json'] + ['-H'] + headers +
    ['-d', '{"email":"invited@test.com","first_name":"Invited","last_name":"User","role":"employee","organization_id":1}'],
    capture_output=True, text=True)
print('Invite:', json.loads(r.stdout))

# List users to find the new one
r = subprocess.run(['curl.exe', '-s', 'http://localhost:8000/super-admin/users?page=1'] + ['-H'] + headers, capture_output=True, text=True)
d = json.loads(r.stdout)
invited = [u for u in d['users'] if u['email'] == 'invited@test.com']
if invited:
    uid = invited[0]['id']
    print(f'Found invited user id={uid}')

    # Disable
    r = subprocess.run(['curl.exe', '-s', '-X', 'PUT', f'http://localhost:8000/super-admin/users/{uid}/disable'] + ['-H'] + headers, capture_output=True, text=True)
    print('Disable:', json.loads(r.stdout))

    # Enable
    r = subprocess.run(['curl.exe', '-s', '-X', 'PUT', f'http://localhost:8000/super-admin/users/{uid}/enable'] + ['-H'] + headers, capture_output=True, text=True)
    print('Enable:', json.loads(r.stdout))

    # Reset password
    r = subprocess.run(['curl.exe', '-s', '-X', 'PUT', f'http://localhost:8000/super-admin/users/{uid}/reset-password',
        '-H', 'Content-Type: application/json'] + ['-H'] + headers +
        ['-d', '{"new_password":"NewPass123!"}'],
        capture_output=True, text=True)
    print('Reset:', json.loads(r.stdout))

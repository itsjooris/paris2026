"""
Paris 2026 — Serveur Flask
"""
from flask import Flask, request, jsonify, send_from_directory
import json, os, hashlib, time

app = Flask(__name__, static_folder='static')
DATA_FILE = os.path.join(os.environ.get('DATA_DIR', os.path.dirname(__file__)), 'data.json')

DEFAULT_DATA = {
    "users": {},
    "bets": {},
    "matches": [
        {"id":"m1",  "phase":"Groupe A", "home":"États-Unis 🇺🇸", "away":"Mexique 🇲🇽",    "date":"11 juin · 19h00", "result": None},
        {"id":"m2",  "phase":"Groupe A", "home":"Canada 🇨🇦",     "away":"Maroc 🇲🇦",      "date":"12 juin · 19h00", "result": None},
        {"id":"m3",  "phase":"Groupe B", "home":"France 🇫🇷",     "away":"Brésil 🇧🇷",     "date":"13 juin · 21h00", "result": None},
        {"id":"m4",  "phase":"Groupe B", "home":"Argentine 🇦🇷",  "away":"Espagne 🇪🇸",    "date":"14 juin · 21h00", "result": None},
        {"id":"m5",  "phase":"Groupe C", "home":"Angleterre 🏴󠁧󠁢󠁥󠁮󠁧󠁿", "away":"Allemagne 🇩🇪",  "date":"15 juin · 19h00", "result": None},
        {"id":"m6",  "phase":"Groupe C", "home":"Portugal 🇵🇹",   "away":"Pays-Bas 🇳🇱",   "date":"16 juin · 19h00", "result": None},
        {"id":"m7",  "phase":"Groupe D", "home":"Belgique 🇧🇪",   "away":"Croatie 🇭🇷",    "date":"17 juin · 19h00", "result": None},
        {"id":"m8",  "phase":"Groupe D", "home":"Japon 🇯🇵",      "away":"Sénégal 🇸🇳",    "date":"18 juin · 19h00", "result": None},
        {"id":"m9",  "phase":"Groupe E", "home":"Uruguay 🇺🇾",    "away":"Colombie 🇨🇴",   "date":"19 juin · 19h00", "result": None},
        {"id":"m10", "phase":"Groupe E", "home":"Italie 🇮🇹",     "away":"Mexique 🇲🇽",    "date":"20 juin · 19h00", "result": None},
        {"id":"m11", "phase":"Groupe F", "home":"Pays-Bas 🇳🇱",   "away":"Sénégal 🇸🇳",   "date":"21 juin · 19h00", "result": None},
        {"id":"m12", "phase":"Groupe F", "home":"Espagne 🇪🇸",    "away":"Japon 🇯🇵",      "date":"22 juin · 19h00", "result": None},
    ]
}

def load():
    if not os.path.exists(DATA_FILE):
        save(DEFAULT_DATA)
        return DEFAULT_DATA
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hp(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def is_admin(data, username):
    u = data['users'].get(username)
    return u and u.get('isAdmin', False)

# ── Static ──────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# ── Auth ────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    b = request.json
    name, pwd = b.get('name','').strip(), b.get('password','')
    if len(name) < 2: return jsonify(error="Pseudo trop court (min. 2 car.)"), 400
    if len(pwd)  < 3: return jsonify(error="Mot de passe trop court (min. 3 car.)"), 400
    data = load()
    if name in data['users']: return jsonify(error="Pseudo déjà pris"), 409
    first = len(data['users']) == 0
    data['users'][name] = {"password": hp(pwd), "isAdmin": first}
    save(data)
    return jsonify(ok=True, isAdmin=first)

@app.route('/api/login', methods=['POST'])
def login():
    b = request.json
    name, pwd = b.get('name','').strip(), b.get('password','')
    data = load()
    u = data['users'].get(name)
    if not u:               return jsonify(error="Pseudo introuvable"), 404
    if u['password'] != hp(pwd): return jsonify(error="Mauvais mot de passe"), 401
    return jsonify(ok=True, isAdmin=u.get('isAdmin', False))

# ── Data ─────────────────────────────────────────────────────
@app.route('/api/data')
def get_data():
    data = load()
    users_safe = {k: {"isAdmin": v["isAdmin"]} for k,v in data['users'].items()}
    return jsonify(users=users_safe, matches=data['matches'], bets=data['bets'])

# ── Bets ─────────────────────────────────────────────────────
@app.route('/api/bet', methods=['POST'])
def bet():
    b = request.json
    username, mid = b.get('username'), b.get('matchId')
    winner = b.get('winner')
    if not all([username, mid, winner]): return jsonify(error="Données manquantes"), 400
    data = load()
    m = next((x for x in data['matches'] if x['id']==mid), None)
    if not m:        return jsonify(error="Match introuvable"), 404
    if m['result']:  return jsonify(error="Match terminé, pari impossible"), 403
    if username not in data['users']: return jsonify(error="Utilisateur inconnu"), 403
    if username not in data['bets']: data['bets'][username] = {}
    data['bets'][username][mid] = {
        "winner": winner,
        "scoreHome": b.get('scoreHome'),
        "scoreAway": b.get('scoreAway')
    }
    save(data)
    return jsonify(ok=True)

# ── Admin ─────────────────────────────────────────────────────
@app.route('/api/admin/match', methods=['POST'])
def add_match():
    b = request.json
    data = load()
    if not is_admin(data, b.get('username')): return jsonify(error="Accès refusé"), 403
    m = {"id": "m"+str(int(time.time()*1000)),
         "phase": b.get('phase','?'), "home": b.get('home'), "away": b.get('away'),
         "date": b.get('date','TBD'), "result": None}
    data['matches'].append(m)
    save(data)
    return jsonify(ok=True, match=m)

@app.route('/api/admin/result', methods=['POST'])
def set_result():
    b = request.json
    data = load()
    if not is_admin(data, b.get('username')): return jsonify(error="Accès refusé"), 403
    m = next((x for x in data['matches'] if x['id']==b.get('matchId')), None)
    if not m: return jsonify(error="Match introuvable"), 404
    m['result'] = {"home": b.get('home'), "away": b.get('away')}
    save(data)
    return jsonify(ok=True)

@app.route('/api/admin/match/<mid>', methods=['DELETE'])
def del_match(mid):
    username = request.args.get('username','')
    data = load()
    if not is_admin(data, username): return jsonify(error="Accès refusé"), 403
    data['matches'] = [x for x in data['matches'] if x['id']!=mid]
    for ub in data['bets'].values(): ub.pop(mid, None)
    save(data)
    return jsonify(ok=True)

@app.route('/api/admin/reset', methods=['POST'])
def reset():
    b = request.json
    data = load()
    if not is_admin(data, b.get('username')): return jsonify(error="Accès refusé"), 403
    save(DEFAULT_DATA)
    return jsonify(ok=True)

@app.route('/api/admin/promote', methods=['POST'])
def promote():
    b = request.json
    data = load()
    if not is_admin(data, b.get('username')): return jsonify(error="Accès refusé"), 403
    target = b.get('target')
    if target not in data['users']: return jsonify(error="Utilisateur introuvable"), 404
    data['users'][target]['isAdmin'] = not data['users'][target].get('isAdmin', False)
    save(data)
    return jsonify(ok=True, isAdmin=data['users'][target]['isAdmin'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)

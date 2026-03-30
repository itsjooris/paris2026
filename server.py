"""
Paris 2026 — Serveur Flask
"""
from flask import Flask, request, jsonify, send_from_directory
import json, os, hashlib, time, urllib.request, threading
from datetime import datetime, timezone, timedelta

app = Flask(__name__, static_folder='static')
DATA_FILE = os.path.join(os.environ.get('DATA_DIR', os.path.dirname(__file__)), 'data.json')

OPENFOOTBALL_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

DEFAULT_DATA = {"users": {}, "bets": {}, "matches": [], "settings": {"invite_code": "", "invite_required": False}}

FLAGS = {
    "Mexico":"Mexique 🇲🇽","South Africa":"Afrique du Sud 🇿🇦","South Korea":"Corée du Sud 🇰🇷",
    "Canada":"Canada 🇨🇦","Qatar":"Qatar 🇶🇦","Switzerland":"Suisse 🇨🇭",
    "Brazil":"Brésil 🇧🇷","Morocco":"Maroc 🇲🇦","Haiti":"Haïti 🇭🇹","Scotland":"Écosse 🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "USA":"États-Unis 🇺🇸","Paraguay":"Paraguay 🇵🇾","Australia":"Australie 🇦🇺",
    "Germany":"Allemagne 🇩🇪","Curaçao":"Curaçao 🇨🇼","Ivory Coast":"Côte d'Ivoire 🇨🇮",
    "Ecuador":"Équateur 🇪🇨","Netherlands":"Pays-Bas 🇳🇱","Japan":"Japon 🇯🇵",
    "Tunisia":"Tunisie 🇹🇳","Belgium":"Belgique 🇧🇪","Egypt":"Égypte 🇪🇬",
    "Iran":"Iran 🇮🇷","New Zealand":"Nouvelle-Zélande 🇳🇿","Spain":"Espagne 🇪🇸",
    "Cape Verde":"Cap-Vert 🇨🇻","Saudi Arabia":"Arabie Saoudite 🇸🇦","Uruguay":"Uruguay 🇺🇾",
    "France":"France 🇫🇷","Senegal":"Sénégal 🇸🇳","Norway":"Norvège 🇳🇴",
    "Argentina":"Argentine 🇦🇷","Algeria":"Algérie 🇩🇿","Austria":"Autriche 🇦🇹",
    "Jordan":"Jordanie 🇯🇴","Portugal":"Portugal 🇵🇹","Uzbekistan":"Ouzbékistan 🇺🇿",
    "Colombia":"Colombie 🇨🇴","England":"Angleterre 🏴󠁧󠁢󠁥󠁮󠁧󠁿","Croatia":"Croatie 🇭🇷",
    "Ghana":"Ghana 🇬🇭","Panama":"Panama 🇵🇦","Poland":"Pologne 🇵🇱",
    "Serbia":"Serbie 🇷🇸","Ukraine":"Ukraine 🇺🇦","Denmark":"Danemark 🇩🇰",
    "Sweden":"Suède 🇸🇪","Turkey":"Turquie 🇹🇷","Cameroon":"Cameroun 🇨🇲",
    "Nigeria":"Nigéria 🇳🇬","Venezuela":"Venezuela 🇻🇪","Chile":"Chili 🇨🇱",
    "Peru":"Pérou 🇵🇪","Costa Rica":"Costa Rica 🇨🇷","Honduras":"Honduras 🇭🇳",
    "Jamaica":"Jamaïque 🇯🇲","Iraq":"Irak 🇮🇶","Indonesia":"Indonésie 🇮🇩",
    "China":"Chine 🇨🇳","Thailand":"Thaïlande 🇹🇭",
}

PHASE_FR = {
    "Group A":"Groupe A","Group B":"Groupe B","Group C":"Groupe C","Group D":"Groupe D",
    "Group E":"Groupe E","Group F":"Groupe F","Group G":"Groupe G","Group H":"Groupe H",
    "Group I":"Groupe I","Group J":"Groupe J","Group K":"Groupe K","Group L":"Groupe L",
    "Round of 32":"Huitièmes","Round of 16":"16e de finale",
    "Quarter-final":"Quart de finale","Semi-final":"Demi-finale",
    "Match for third place":"Petite finale","Final":"Finale",
}

UTC_OFFSETS = {"UTC-4":-4,"UTC-5":-5,"UTC-6":-6,"UTC-7":-7}
MONTHS_FR   = {1:"jan",2:"fév",3:"mar",4:"avr",5:"mai",6:"juin",
               7:"juil",8:"août",9:"sep",10:"oct",11:"nov",12:"déc"}

def translate_team(name):
    return FLAGS.get(name, name)

def convert_to_paris_time(date_str, time_str):
    try:
        parts    = time_str.strip().split()
        hm       = parts[0]
        tz_str   = parts[1] if len(parts) > 1 else "UTC-5"
        offset_h = UTC_OFFSETS.get(tz_str, -5)
        h, m     = map(int, hm.split(':'))
        y, mo, d = map(int, date_str.split('-'))
        local_dt = datetime(y, mo, d, h, m, tzinfo=timezone(timedelta(hours=offset_h)))
        paris_dt = local_dt.astimezone(timezone.utc).astimezone(timezone(timedelta(hours=2)))
        return f"{paris_dt.day} {MONTHS_FR[paris_dt.month]} · {paris_dt.strftime('%Hh%M')}"
    except Exception:
        return date_str

def import_from_openfootball(raw):
    matches = []
    for i, m in enumerate(raw.get("matches", [])):
        team1      = m.get("team1", "")
        team2      = m.get("team2", "")
        round_name = m.get("round", "")
        group      = m.get("group", "")
        date       = m.get("date", "")
        time_raw   = m.get("time", "")
        ground     = m.get("ground", "")
        num        = m.get("num")

        phase = PHASE_FR.get(group, PHASE_FR.get(round_name, round_name))

        def fmt_team(t, side):
            if not t or t.startswith("W") or t.startswith("L") or (t and t[0].isdigit() and len(t) <= 4):
                return f"Qualifié M{num} ({side})" if num else "À déterminer"
            return translate_team(t)

        home    = fmt_team(team1, "dom")
        away    = fmt_team(team2, "ext")
        date_fr = convert_to_paris_time(date, time_raw) if date and time_raw else date

        score  = m.get("score")
        result = None
        if score and score.get("ft"):
            ft = score["ft"]
            result = {"home": ft[0], "away": ft[1]}

        matches.append({"id": f"of_{i+1}", "phase": phase, "home": home,
                        "away": away, "date": date_fr, "ground": ground, "result": result})
    return matches

def fetch_openfootball():
    req = urllib.request.Request(OPENFOOTBALL_URL, headers={'User-Agent': 'Paris2026/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))

def auto_import_matches():
    """Import automatique au démarrage si aucun match en base."""
    try:
        data = load()
        if len(data.get('matches', [])) == 0:
            print("[Paris2026] Aucun match — import automatique...")
            raw     = fetch_openfootball()
            matches = import_from_openfootball(raw)
            data['matches'] = matches
            save(data)
            print(f"[Paris2026] ✅ {len(matches)} matchs importés.")
        else:
            print(f"[Paris2026] {len(data['matches'])} matchs déjà en base.")
    except Exception as e:
        print(f"[Paris2026] ⚠️  Import auto échoué : {e}")

def validate_bet(winner, score_home, score_away):
    """Vérifie la cohérence vainqueur/score. Retourne (ok, message)."""
    if score_home is None or score_away is None:
        return True, None  # Pas de score saisi, rien à valider
    sh, sa = int(score_home), int(score_away)
    if winner == 'home' and sa > sh:
        return False, "Score incohérent : tu as choisi l'équipe domicile gagnante mais le score indique une victoire extérieure."
    if winner == 'away' and sh > sa:
        return False, "Score incohérent : tu as choisi l'équipe extérieure gagnante mais le score indique une victoire domicile."
    if winner == 'draw' and sh != sa:
        return False, "Score incohérent : tu as choisi un match nul mais le score n'est pas égal."
    return True, None

# ── I/O ──────────────────────────────────────────────────────
def load():
    if not os.path.exists(DATA_FILE):
        save(DEFAULT_DATA)
        return dict(DEFAULT_DATA)
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

# ── Static ────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# ── Auth ──────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    b = request.json
    name, pwd = b.get('name','').strip(), b.get('password','')
    if len(name) < 2: return jsonify(error="Pseudo trop court (min. 2 car.)"), 400
    if len(pwd)  < 3: return jsonify(error="Mot de passe trop court (min. 3 car.)"), 400
    data = load()
    settings = data.get('settings', DEFAULT_DATA['settings'])
    first = len(data['users']) == 0
    if not first and settings.get('invite_required') and settings.get('invite_code'):
        code = b.get('invite_code', '').strip()
        if code != settings['invite_code']:
            return jsonify(error="Code d'invitation invalide"), 403
    if name in data['users']: return jsonify(error="Pseudo déjà pris"), 409
    data['users'][name] = {"password": hp(pwd), "isAdmin": first}
    save(data)
    return jsonify(ok=True, isAdmin=first)

@app.route('/api/login', methods=['POST'])
def login():
    b = request.json
    name, pwd = b.get('name','').strip(), b.get('password','')
    data = load()
    u = data['users'].get(name)
    if not u:                    return jsonify(error="Pseudo introuvable"), 404
    if u['password'] != hp(pwd): return jsonify(error="Mauvais mot de passe"), 401
    return jsonify(ok=True, isAdmin=u.get('isAdmin', False))

# ── Data ──────────────────────────────────────────────────────
@app.route('/api/data')
def get_data():
    data = load()
    settings = data.get('settings', DEFAULT_DATA['settings'])
    users_safe = {k: {"isAdmin": v["isAdmin"]} for k,v in data['users'].items()}
    return jsonify(users=users_safe, matches=data['matches'], bets=data['bets'],
                   invite_required=settings.get('invite_required', False))

# ── Bets ──────────────────────────────────────────────────────
@app.route('/api/bet', methods=['POST'])
def bet():
    b = request.json
    username  = b.get('username')
    mid       = b.get('matchId')
    winner    = b.get('winner')
    score_home = b.get('scoreHome')
    score_away = b.get('scoreAway')

    if not all([username, mid, winner]):
        return jsonify(error="Données manquantes"), 400

    # Validation cohérence vainqueur / score
    ok, msg = validate_bet(winner, score_home, score_away)
    if not ok:
        return jsonify(error=msg), 400

    data = load()
    m = next((x for x in data['matches'] if x['id']==mid), None)
    if not m:       return jsonify(error="Match introuvable"), 404
    if m['result']: return jsonify(error="Match terminé, pari impossible"), 403
    if username not in data['users']: return jsonify(error="Utilisateur inconnu"), 403

    if username not in data['bets']: data['bets'][username] = {}
    data['bets'][username][mid] = {
        "winner": winner, "scoreHome": score_home, "scoreAway": score_away
    }
    save(data)
    return jsonify(ok=True)

# ── Admin — Import ────────────────────────────────────────────
@app.route('/api/admin/import', methods=['POST'])
def import_matches():
    b = request.json
    data = load()
    if not is_admin(data, b.get('username')): return jsonify(error="Accès refusé"), 403
    replace = b.get('replace', False)
    try:
        raw = fetch_openfootball()
    except Exception as e:
        return jsonify(error=f"Impossible de récupérer les données : {str(e)}"), 502

    new_matches = import_from_openfootball(raw)
    if replace:
        existing_results = {m['id']: m['result'] for m in data['matches'] if m.get('result')}
        for m in new_matches:
            if m['id'] in existing_results:
                m['result'] = existing_results[m['id']]
        data['matches'] = new_matches
        count = len(new_matches)
    else:
        existing_ids = {m['id'] for m in data['matches']}
        added = [m for m in new_matches if m['id'] not in existing_ids]
        data['matches'].extend(added)
        count = len(added)

    save(data)
    return jsonify(ok=True, imported=count, total=len(data['matches']))

# ── Admin — Sync résultats ────────────────────────────────────
@app.route('/api/admin/sync', methods=['POST'])
def sync_results():
    b = request.json
    data = load()
    if not is_admin(data, b.get('username')): return jsonify(error="Accès refusé"), 403
    try:
        raw = fetch_openfootball()
    except Exception as e:
        return jsonify(error=f"Impossible de récupérer les données : {str(e)}"), 502

    result_map = {m['id']: m['result'] for m in import_from_openfootball(raw) if m.get('result')}
    updated = 0
    for m in data['matches']:
        if m['id'] in result_map and not m.get('result'):
            m['result'] = result_map[m['id']]
            updated += 1
    save(data)
    return jsonify(ok=True, updated=updated)

# ── Admin — CRUD ──────────────────────────────────────────────
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
    data['matches'] = []
    data['bets']    = {}
    save(data)
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

@app.route('/api/admin/user/<target>', methods=['DELETE'])
def del_user(target):
    username = request.args.get('username','')
    data = load()
    if not is_admin(data, username): return jsonify(error="Accès refusé"), 403
    if target == username: return jsonify(error="Tu ne peux pas te supprimer toi-même"), 400
    if target not in data['users']: return jsonify(error="Utilisateur introuvable"), 404
    del data['users'][target]
    data['bets'].pop(target, None)
    save(data)
    return jsonify(ok=True)

# ── Admin — Settings ─────────────────────────────────────────
@app.route('/api/admin/settings', methods=['GET'])
def get_settings():
    username = request.args.get('username','')
    data = load()
    if not is_admin(data, username): return jsonify(error="Accès refusé"), 403
    settings = data.get('settings', DEFAULT_DATA['settings'])
    return jsonify(ok=True, settings=settings)

@app.route('/api/admin/settings', methods=['POST'])
def update_settings():
    b = request.json
    data = load()
    if not is_admin(data, b.get('username')): return jsonify(error="Accès refusé"), 403
    if 'settings' not in data:
        data['settings'] = dict(DEFAULT_DATA['settings'])
    if 'invite_code' in b:
        data['settings']['invite_code'] = b['invite_code'].strip()
    if 'invite_required' in b:
        data['settings']['invite_required'] = bool(b['invite_required'])
    save(data)
    return jsonify(ok=True, settings=data['settings'])

# ── Démarrage ─────────────────────────────────────────────────
threading.Thread(target=auto_import_matches, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)

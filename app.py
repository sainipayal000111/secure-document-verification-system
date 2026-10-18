
from flask import Flask, render_template, request, redirect, session
import mysql.connector
import hashlib, json, os, datetime

app = Flask(__name__)
app.secret_key = "blockvote123"
os.makedirs("uploads", exist_ok=True)

def get_db():
    return mysql.connector.connect(host="localhost", user="root", password="", database="blockvote")

def add_block(data):
    chain = []
    if os.path.exists('blockchain.json'):
        chain = json.load(open('blockchain.json'))
    prev = chain[-1]['hash'] if chain else "0"
    block = {"index": len(chain)+1, "time": str(datetime.datetime.now()), "data": data, "prev": prev}
    block["hash"] = hashlib.sha256(json.dumps(block).encode()).hexdigest()
    chain.append(block)
    json.dump(chain, open('blockchain.json','w'), indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        vid = request.form['voter_id']
        pwd = request.form['password']
        doc = request.files['doc']
        doc.save(f"uploads/{doc.filename}")
        h = hashlib.sha256((vid+doc.filename).encode()).hexdigest()
        add_block(f"Document: {vid} Hash: {h[:10]}")
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO voters (name, voter_id, password, doc_name, doc_hash) VALUES (%s,%s,%s,%s,%s)", (name, vid, pwd, doc.filename, h))
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            return "Ye Voter ID pehle se hai"
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        vid = request.form['voter_id']
        pwd = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM voters WHERE voter_id=%s AND password=%s", (vid, pwd))
        user = cur.fetchone()
        conn.close()
        if user:
            if user[6] != 'Approved':
                return "Pehle Admin se Verify karwao"
            session['vid'] = vid
            return redirect('/vote')
        return "Galat ID/Password"
    return render_template('login.html')

@app.route('/vote', methods=['GET','POST'])
def vote():
    if 'vid' not in session:
        return redirect('/login')
    if request.method == 'POST':
        cand = request.form['candidate']
        vid = session['vid']
        h = hashlib.sha256((vid+cand).encode()).hexdigest()
        add_block(f"Vote: {vid} -> {cand}")
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO votes (voter_id, candidate, vote_hash) VALUES (%s,%s,%s)", (vid, cand, h))
            conn.commit()
            conn.close()
            return "Vote Successful! <a href='/result'>Result Dekho</a>"
        except:
            return "Tum pehle hi Vote de chuke ho"
    return render_template('vote.html')

@app.route('/admin')
def admin():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM voters")
    voters = cur.fetchall()
    conn.close()
    chain = json.load(open('blockchain.json')) if os.path.exists('blockchain.json') else []
    return render_template('admin.html', voters=voters, chain=chain)

@app.route('/approve/<vid>')
def approve(vid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE voters SET status='Approved' WHERE voter_id=%s", (vid,))
    conn.commit()
    conn.close()
    add_block(f"Approved: {vid}")
    return redirect('/admin')

@app.route('/result')
def result():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT candidate, COUNT(*) FROM votes GROUP BY candidate")
    data = cur.fetchall()
    conn.close()
    return render_template('result.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)

Creating a player: u = User.objects.create_user(username="proof_user", password="test1234")
Creating a user: p = Player.objects.create(user=u)

Creating a question: q1 = Question.objects.create(faction=Faction.RIGHT, order=1, text="Scenario 1: A new technology has emerged! Oh no!", option1="Since memory is a right, it should be banned!", option2="Same!", option3="same!")
Updating a question's text: q1.text = "Scenario 1 change: Evil Megacorp TM has been defeated!"
Saving it: q1.save()

Linking a player to a question:
a = Answer.objects.create(player=p, question=q1, choice=2) # of q1, player has chosen option 3: "same!"

Deleting it: 
q1_id = q1.id
q1.delete() # questions are identified and deleted via their id

Creating a new login:
c = Client() # simulates a new user
c.login(username="proof_user", password="test1234") # the user has logged in with their username and password

# the user has selected the RIGHTISTS faction
    resp = c.post(
        "/api/select-faction/",
        data=json.dumps({"faction": int(Faction.RIGHT)}),
        content_type="application/json",
    )

# checking if the faction selection was correct
 print("POST /api/select-faction/ ->", resp.status_code)

# selecting an question ID to answer
q_for_answer = Question.objects.order_by("id").first()
qid = q_for_answer.id if q_for_answer else 1

# the user posts an answer (i.e. option 2)
resp = c.post(
        "/api/answer/",
        data=json.dumps({"qid": int(qid), "choice": 1}),
        content_type="application/json",
    )

problem: this isn't firebase. how do we implement firebase.
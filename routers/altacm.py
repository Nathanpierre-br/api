from datetime import UTC, datetime
from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.config import Config
from helpers.database.mongo import Database
from helpers.decorators.validauth import validauth_required
from helpers.routers.cachable import CachableRoute
from objects import Base, Errors
from objects.types import UserRole

altacm = APIRouter()
altacm.route_class = CachableRoute



@altacm.post("/altacm/s/community/x{ndcId}/user/{userId}/promote")
@altacm.delete("/altacm/s/community/x{ndcId}/user/{userId}/promote")
@validauth_required
async def promotions(request: Request, ndcId: int, userId: str):
	t1 = timestamp()

	trigger_uid = request.state.session["uid"]
	destruction_mode = request.method == "DELETE"
	if not destruction_mode:
		data = await request.json()
		role = data.get("role")
		if role is None or role < 100 or role > 102:
			return Errors.InvalidRequest()
	else:
		role = 0
 

	db = await Database().init()
	sensitive_table = db.get(table="Users")
	ndc_users_table = db.get(f"x{ndcId}", "Users")

	user = await sensitive_table.find_one({"id": trigger_uid})
	gu = await sensitive_table.find_one({"id": userId})
	f = UserRole.is_local_admin if role != UserRole.Agent else lambda r: r == UserRole.Agent
	if not gu or not f(role):
		if not user or not UserRole.is_global_staff(user.get("role", 0)):
			db.close()
			return Errors.NotEnoughRights(timestamp() - t1)

	await ndc_users_table.update_one({"id": userId}, {"$set": {"role": role}})

	return Base.Answer(spent_time=timestamp() - t1)

@altacm.post("/altacm/s/community/create")
@validauth_required
async def create_community(request: Request):
	t1 = timestamp()

	trigger_uid = request.state.session["uid"]
	data = await request.json()

	fields = ["name", "aminoId", "lang"]
	missing_fields = [field for field in fields if field not in data]
	if missing_fields:
		return Errors.InvalidRequest(timestamp() - t1)

	db = await Database().init()
	try:
		sensitive_table = db.get(table="Users")

		user = await sensitive_table.find_one({"id": trigger_uid})
		if not user or not UserRole.is_global_staff(user.get("role", 0)):
			# For now, we will prohibit the creation of communities by users themselves.
			db.close()
			return Errors.NotEnoughRights(timestamp() - t1)

		ndclist_table = db.get(table="Communities")
		
		existing_community = await ndclist_table.find_one({"aminoId": data["aminoId"]})
		if existing_community:
			db.close()
			return Errors.Exs9(timestamp() - t1) 

		is_staff = UserRole.is_global_staff(user.get("role", 0))
		agentAminoId = None

		if "agentGlobalLink" in data and data["agentGlobalLink"]:
			if not is_staff:
				db.close()
				return Errors.NotEnoughRights(timestamp() - t1)
				
			if f"{Config.SITE_DOMAIN}/u/" not in data["agentGlobalLink"]:
				db.close()
				return Errors.InvalidRequest(timestamp() - t1)
				
			agentAminoId = data["agentGlobalLink"].split("/")[-1]
		else:
			agentAminoId = user.get("aminoId")
			if not agentAminoId:
				db.close()
				return Errors.InternalServerError(timestamp() - t1)

		latest_community = await ndclist_table.find_one(sort=[("id", -1)])
		if latest_community and latest_community.get("id"):
			ndcId = latest_community["id"] + 1
		else:
			ndcId = 1

		shape = await ndclist_table.find_one({"id": 0})
		if not shape:
			db.close()
			return Errors.InternalServerError(timestamp() - t1)

		shape["id"] = ndcId
		shape["name"] = data["name"]
		shape["aminoId"] = data["aminoId"]
		shape["lang"] = data["lang"] if data["lang"] in ["en", "ru", "es", "ar"] else "en"
		for key in ["_id", "theme"]:
			shape.pop(key, None)

		aminoIds = ["teamaltamino", "astral", agentAminoId]
		global_table = db.get("x0", "Users")
		new_users_table = db.get(f"x{ndcId}", "Users")
		who_joined = []
		
		for aminoId in aminoIds:
			aid2id_request = await sensitive_table.find_one(
				{"aminoId": aminoId}, projection={"id": 1, "_id": 0}
			)

			if not aid2id_request and aminoId != "astral":
				db.close()
				return Errors.InternalServerError(timestamp() - t1)

			if not aid2id_request and aminoId == "astral":
				continue

			uid = aid2id_request["id"]
			
			if uid in who_joined:
				continue

			profile = await global_table.find_one({"id": uid})
			if not profile:
				db.close()
				return Errors.InternalServerError(timestamp() - t1)

			modtime = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
			profile.pop("_id", None)
			profile["wall"] = {}
			profile["whoFollows"] = []
			profile["following"] = []
			profile["titles"] = []
			profile["savedBlogs"] = []
			profile["consecutiveDaysOfCheckIns"] = 0
			profile["reputation"] = 0
			profile["minutesPerDay"] = 0
			profile["minutesPerWeek"] = 0
			profile["createdTime"] = modtime
			profile["modifiedTime"] = modtime
			
			if aminoId == agentAminoId:
				shape["agent"] = uid
				profile["role"] = 102

			await new_users_table.insert_one(profile)
			who_joined.append(uid)

		shape["memberList"] = who_joined
		shape["membersCount"] = len(who_joined)
		await ndclist_table.insert_one(shape)

		await sensitive_table.update_many(
			{"id": {"$in": who_joined}},
			{"$addToSet": {"communityList": ndcId}},
		)

		return Base.Answer({
			"community": {
				"ndcId": shape["id"],
				"name": shape["name"],
				"aminoId": shape["aminoId"],
				"lang": shape["lang"],
				"membersCount": shape["membersCount"],
				"icon": shape.get("icon")
				}
			},
			spent_time=timestamp() - t1
		)
	finally:
		db.close()

@altacm.delete("/altacm/s/community/x{ndcId}/destroy")
@validauth_required
async def destroy_community(request: Request, ndcId: int):
	t1 = timestamp()

	# how you dare destroying community!
	#
	# btw it can helps if there is some
	# malicious community going around
	# that can hurt us in any ways

	trigger_uid = request.state.session["uid"]

	# do you even have rights to do this act?
	db = Database()
	sensitive_table = db.get(table="Users")

	user = await sensitive_table.find_one({"id": trigger_uid})
	if not user or not UserRole.is_global_staff(user.get("role", 0)):
		db.close()
		return Errors.NotEnoughRights(timestamp() - t1)

	# well.. fine. we will delete everything
	# starting from communities table
	ndclist_table = db.get(table="Communities")
	await ndclist_table.delete_one({"id": ndcId})

	# now we can nuke community database
	await db.connection.drop_database(f"x{ndcId}")

	# but what about who joined community?
	condition = {"communityList": ndcId}
	await sensitive_table.update_many(condition, {"$pull": condition})

	# *sigh*... we are done.    // bro wtf??? -_-
	db.close()
	return Base.Answer(spent_time=timestamp() - t1)



@altacm.post("/altacm/s/community/x{ndcId}/edit")
@validauth_required
async def edit_community(request: Request, ndcId: int = 0):
	t1 = timestamp()

	trigger_uid = request.state.session["uid"]
	data = await request.json()
	conf = data.get("configuration", {})

	db = await Database().init()
	try:
		global_users_table = db.get(table="Users")
		global_user = await global_users_table.find_one({"id": trigger_uid})
		
		is_global = global_user and UserRole.is_global_staff(global_user.get("role", 0))
		is_allowed = is_global

		if not is_allowed:
			local_users_table = db.get(f"x{ndcId}", "Users")
			local_user = await local_users_table.find_one({"id": trigger_uid})
			
			if local_user and local_user.get("role", 0) in (UserRole.Leader, UserRole.Agent):
				is_allowed = True

		if not is_allowed:
			return Errors.NotEnoughRights(timestamp() - t1)

		preparedQueries = {
			"configuration": {},
			"modifiedTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
		}

		for key in [
			"name",
			"aminoId",
			"tagline",
			"description",
			"guidelines",
			"icon",
			"themeUrl",
			"themeColor",
			"themeRevision",
			"coverUrl",
		]:
			if key in data:
				preparedQueries[key] = data[key]


		if is_global:
			if "lang" in data:
				lang_val = data["lang"]
				preparedQueries["lang"] = lang_val if lang_val in ["en", "ru", "es", "ar"] else "en"
			
			try:
				if "joinType" in conf:
					preparedQueries["joinType"] = int(conf["joinType"]) if conf["joinType"] in [0, 1, 2] else 0
				if "hidden" in conf:
					preparedQueries["hidden"] = bool(conf["hidden"])
			except:
				return Errors.InvalidRequest(timestamp() - t1)


		for key in ["welcomeMessage", "welcomeMessageEnabled"]:
			if key in conf:
				preparedQueries["configuration"][key] = conf[key]

		if not preparedQueries["configuration"]:
			preparedQueries.pop("configuration")

		communities_table = db.get(table="Communities")
		
		if "aminoId" in preparedQueries:
			existing_community = await communities_table.find_one({
				"aminoId": preparedQueries["aminoId"],
				"id": {"$ne": ndcId}
			})
			if existing_community:
				return Errors.Exs9(timestamp() - t1) 
		
		await communities_table.update_one({"id": ndcId}, {"$set": preparedQueries})

		return Base.Answer({}, spent_time=timestamp() - t1)
		
	finally:
		db.close()


@altacm.post("/altacm/s/community/x{ndcId}/theme-pack")
@validauth_required
async def get_community_themePack(request: Request, ndcId: int = 0):
	t1 = timestamp()

	trigger_uid = request.state.session["uid"]

	db = await Database().init()
	try:
		global_users_table = db.get(table="Users")
		global_user = await global_users_table.find_one({"id": trigger_uid})
		
		is_global = global_user and UserRole.is_global_staff(global_user.get("role", 0))
		is_allowed = is_global

		if not is_allowed:
			local_users_table = db.get(f"x{ndcId}", "Users")
			local_user = await local_users_table.find_one({"id": trigger_uid})
			
			if local_user and local_user.get("role", 0) in (UserRole.Leader, UserRole.Agent):
				is_allowed = True

		if not is_allowed:
			return Errors.NotEnoughRights(timestamp() - t1)

		communities_table = db.get(table="Communities")
		theme = await communities_table.find_one({"id": ndcId}, projection={"themeUrl": 1, 'themeRevision': 1, "themeColor": 1, "_id": 0})
		return Base.Answer({"themeUrl": theme.get("themeUrl"), "themeRevision": theme.get("themeRevision"), "themeColor": theme.get("themeColor")}, spent_time=timestamp() - t1)
		
	finally:
		db.close()





@altacm.get("/altacm/s/user-profile/{userId}/moderated-communities")
@validauth_required
async def communities_with_role(request: Request, userId: str):
	t1 = timestamp()
	trigger_uid = request.state.session["uid"]

	db = await Database().init()
	try:
		users = db.get(table="Users")

		trigger_user = await users.find_one({"id": trigger_uid})
		if (
			not trigger_user
			or (
				trigger_uid != userId
				and not UserRole.is_global_staff(trigger_user.get("role", 0))
			)
		):
			return Errors.NotEnoughRights(timestamp() - t1)

		target_user = await users.find_one(
			{"id": userId},
			projection={"communityList": 1, "_id": 0},
		)
		if not target_user:
			return Errors.AccountNotExist(timestamp() - t1)

		community_ids = [i for i in target_user.get("communityList", []) if i]

		matching_ndc_ids = []
		for ndcId in community_ids:
			community_users = db.get(database=f"x{ndcId}", table="Users")
			
			member = await community_users.find_one(
				{"id": userId},
				projection={"role": 1, "_id": 0},
			)

			if member and member.get("role") in (UserRole.Leader, UserRole.Agent):
				matching_ndc_ids.append(ndcId)

		return Base.Answer(
			{"communityIdList": matching_ndc_ids},
			spent_time=timestamp() - t1,
		)
	finally:
		db.close()
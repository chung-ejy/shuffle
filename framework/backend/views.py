from django.shortcuts import render
from django.http.response import JsonResponse
from django.views.decorators import csrf
import pandas as pd
import json
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
follower_based = True
# Create your views here.
client = MongoClient("localhost",27017)
@csrf_exempt
def backendView(request):
    data = json.loads(request.body.decode("utf-8"))
    db = client["spotify"]
    table = db["songs"]
    query = table.find({"artist_name":data["artist_name"],"track_name":data["track_name"]},show_record_id=False)
    current = pd.DataFrame(list(query)).iloc[0]
    try:
        max_songs = 10
        artist = current["artist_name"]
        song = current["track_name"]
        current_pid = current["pid"]
        uri = current["track_uri"]
        db = client["spotify"]
        table = db["songs"]
        data = table.find({"track_uri":uri},show_record_id=False)
        included_playlists = list(pd.DataFrame(list(data))["pid"])
        aggregate = []
        pl_aggregate = []
        for pid in included_playlists:
            if pid != current_pid:
                table = db["songs"]
                data = table.find({"pid":pid},show_record_id=False)
                songs = pd.DataFrame(list(data))
                table = db["playlists"]
                data = table.find({"pid":pid},show_record_id=False)
                pl_info = pd.DataFrame(list(data))
                pl_aggregate.append(pl_info)
                aggregate.append(songs)
        client.close()
        s = pd.concat(aggregate)
        p = pd.concat(pl_aggregate)
        if follower_based:
            s = s.merge(p[["pid","num_followers"]],on="pid",how="left")
            max_follower = s["num_followers"].max()
            s["follower_percentage"] = s["num_followers"] / max_follower
            s["count"] = 1 * s["follower_percentage"]
        else:
            s["count"] = 1
        analysis = s.groupby(["track_uri","artist_uri","artist_name","track_name"]).sum().reset_index()
        recs = analysis.sort_values("count",ascending=False)
        rec = recs[(recs["track_name"] != song)].sort_values("count",ascending=False).iloc[:max_songs]
        complete = {"artist_name":current["artist_name"],"track_name":current["track_name"],"pl":list(rec[["artist_name","track_name"]].to_dict("records"))}
    except Exception as e:
        print(str(e))
        complete = {"artist_name":"unknown","track_name":"unknown","pl":[]}
    return JsonResponse(complete,safe=False)
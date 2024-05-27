matches = pd.read_csv("matches.csv", index_col=0)

matches["Date"] = pd.to_datetime(matches["Date"])

matches["venue_code"] = matches["Venue"].astype("category").cat.codes

matches["opp_code"] = matches["Opponent"].astype("category").cat.codes

matches["hour"] = matches["Time"].str.replace(":.+", "", regex=True).astype("int")

matches["day_code"] = matches["Date"].dt.dayofweek

matches["target"] = (matches["Result"] == "W").astype("int")

from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(n_estimators=50, min_samples_split=10, random_state=1)

train = matches[matches["Date"] < '2024-01-01']

test = matches[matches["Date"] > '2024-01-01']

predictors = ["venue_code", "opp_code", "hour", "day_code"]

rf.fit(train[predictors], train["target"])

preds = rf.predict(test[predictors])

from sklearn.metrics import accuracy_score

acc = accuracy_score(test["target"], preds)

combined = pd.DataFrame(dict(actual=test["target"], prediction=preds))

pd.crosstab(index=combined["actual"], columns=combined["prediction"])

from sklearn.metrics import precision_score

grouped_matches = matches.groupby("Team")

group = grouped_matches.get_group("Manchester City")

def rolling_averages(group, cols, new_cols):
  group = group.sort_values("Date")
  rolling_stats = group[cols].rolling(3, closed='left').mean()
  group[new_cols] = rolling_stats
  group = group.dropna(subset=new_cols)
  return group

cols = ["GF", "GA", "Sh", "SoT", "Dist", "FK", "PK", "PKatt"]

new_cols = [f"{c}_rolling" for c in cols]

matches_rolling = matches.groupby("Team").apply(lambda x: rolling_averages(x, cols, new_cols))

matches_rolling = matches_rolling.droplevel("Team")

matches_rolling.index = range(matches_rolling.shape[0])

def make_predictions(data, predictors):

  train = data[data["Date"] < '2024-01-01']
  
  test = data[data["Date"] > '2024-01-01']

  rf.fit(train[predictors], train["target"])
  
  preds = rf.predict(test[predictors])

  combined = pd.DataFrame(dict(actual=test["target"], prediction=preds), index=test.index)

  precision = precision_score(test["target"], preds)

  return combined, precision

combined, precision = make_predictions(matches_rolling, predictors + new_cols)

combined = combined.merge(matches_rolling[["Date", "Team", "Opponent", "Result"]], left_index=True, right_index=True)

class MissingDict(dict):
   def __missing__(self, key):
        # Return the key itself if it is missing
        return key

map_values = {
    "Brighton and Hove Albion":"Brighton",
    "Manchester United":"Manchester Utd",
    "Newcastle United":"Newcastle Utd",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers":"Wolves"
}

mapping = MissingDict(**map_values)

combined["new_team"] = combined["Team"].map(mapping)

merged = combined.merge(combined, left_on=["Date", "new_team"], right_on=["Date", "Opponent"])

merged[(merged["prediction_x"] == 1) & (merged["prediction_y"] == 0)]["actual_x"].value_counts()

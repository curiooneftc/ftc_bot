TEAMS_PER_PAGE = 10

SCOUT_QUERY = """
query EventByCode($season: Int!, $code: String!) {
  eventByCode(season: $season, code: $code) {
    name
    code
    finished
    fieldCount
    ongoing
    started
    teams {
      teamNumber
      stats {
        ... on TeamEventStats2025 {
          rank
          avg {
            totalPoints
            totalPointsNp
          }
          wins
          losses
        }
      }
      team {
        name
      }
    }
  }
}
"""
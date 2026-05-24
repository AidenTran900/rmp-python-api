import requests
from dataclasses import dataclass

API_LINK = "https://www.ratemyprofessors.com/graphql"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/json",
    "Authorization": "Basic dGVzdDp0ZXN0",
    "Sec-GPC": "1",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=4",
}

TEACHER_QUERY = """
query TeacherSearchResultsPageQuery(
  $query: TeacherSearchQuery!
  $schoolID: ID
  $includeSchoolFilter: Boolean!
) {
  search: newSearch {
    teachers(query: $query, first: 8, after: "") {
      edges {
        cursor
        node {
          id
          legacyId
          avgRating
          numRatings
          wouldTakeAgainPercent
          avgDifficulty
          department
          firstName
          lastName
          isSaved
          school {
            name
            id
          }
          __typename
        }
      }
    }
  }
  school: node(id: $schoolID) @include(if: $includeSchoolFilter) {
    __typename
    ... on School {
      name
    }
    id
  }
}
"""

SCHOOL_QUERY = """
query NewSearchSchoolsQuery($query: SchoolSearchQuery!) {
  newSearch {
    schools(query: $query) {
      edges {
        cursor
        node {
          id
          legacyId
          name
          city
          state
          departments {
            id
            name
          }
          numRatings
          avgRatingRounded
          summary {
            campusCondition
            campusLocation
            careerOpportunities
            clubAndEventActivities
            foodQuality
            internetSpeed
            libraryCondition
            schoolReputation
            schoolSafety
            schoolSatisfaction
            socialActivities
          }
        }
      }
    }
  }
}
"""


@dataclass
class ProfessorRating:
    avg_rating: float
    avg_difficulty: float
    would_take_again_percent: float
    num_ratings: int
    formatted_name: str
    department: str
    link: str


def search_schools(school_name: str) -> list[dict] | None:
    try:
        response = requests.post(
            API_LINK,
            headers=HEADERS,
            json={
                "query": SCHOOL_QUERY,
                "variables": {"query": {"text": school_name}},
            },
        )
        response.raise_for_status()
        return response.json()["data"]["newSearch"]["schools"]["edges"]
    except Exception as e:
        print(f"Error searching school: {e}")
        return None


def search_professors(professor_name: str, school_id: str) -> list[dict] | None:
    try:
        response = requests.post(
            API_LINK,
            headers=HEADERS,
            json={
                "query": TEACHER_QUERY,
                "variables": {
                    "query": {
                        "text": professor_name,
                        "schoolID": school_id,
                        "fallback": True,
                        "departmentID": None,
                    },
                    "schoolID": school_id,
                    "includeSchoolFilter": True,
                },
            },
        )
        response.raise_for_status()
        return response.json()["data"]["search"]["teachers"]["edges"]
    except Exception as e:
        print(f"Error searching professors: {e}")
        return None


def get_professor_summary(professor_name: str, school_id: str) -> ProfessorRating:
    results = search_professors(professor_name, school_id)

    if not results:
        return ProfessorRating(
            avg_rating=-1,
            avg_difficulty=-1,
            would_take_again_percent=-1,
            num_ratings=0,
            formatted_name=professor_name,
            department="",
            link="",
        )

    node = results[0]["node"]
    return ProfessorRating(
        avg_rating=node["avgRating"],
        avg_difficulty=node["avgDifficulty"],
        would_take_again_percent=node["wouldTakeAgainPercent"],
        num_ratings=node["numRatings"],
        formatted_name=f"{node['firstName']} {node['lastName']}",
        department=node["department"],
        link=f"https://www.ratemyprofessors.com/professor/{node['legacyId']}",
    )

RATINGS_LIST_QUERY = """
query RatingsListQuery(
  $count: Int!
  $id: ID!
  $courseFilter: String
  $cursor: String
) {
  node(id: $id) {
    __typename
    ... on Teacher {
      id
      legacyId
      lastName
      numRatings
      school {
        id
        legacyId
        name
        city
        state
        avgRating
        numRatings
      }
      ratings(first: $count, after: $cursor, courseFilter: $courseFilter) {
        edges {
          cursor
          node {
            id
            legacyId
            comment
            date
            class
            helpfulRating
            clarityRating
            difficultyRating
            ratingTags
            flagStatus
            createdByUser
            attendanceMandatory
            wouldTakeAgain
            grade
            textbookUse
            isForOnlineClass
            isForCredit
            thumbsUpTotal
            thumbsDownTotal
            teacherNote {
              id
              teacherId
              comment
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    id
  }
}
"""


@dataclass
class Rating:
    id: str
    legacy_id: int
    comment: str
    date: str
    course: str
    helpful_rating: float
    clarity_rating: float
    difficulty_rating: float
    rating_tags: list[str]
    flag_status: str
    attendance_mandatory: str | None
    would_take_again: int | None
    grade: str | None
    textbook_use: int | None
    is_for_online_class: bool
    is_for_credit: bool
    thumbs_up_total: int
    thumbs_down_total: int
    teacher_note: str | None  # comment from professor, if any


def get_ratings_page(
    professor_id: str,
    count: int = 20,
    course_filter: str | None = None,
    cursor: str | None = None,
) -> tuple[list[Rating], bool, str | None]:
    """
    Fetch individual ratings for a professor by their RMP node ID.

    Returns:
        - list of Rating objects
        - has_next_page (bool) for pagination
        - end_cursor (str | None) to pass as `cursor` in the next call
    """
    try:
        response = requests.post(
            API_LINK,
            headers=HEADERS,
            json={
                "query": RATINGS_LIST_QUERY,
                "variables": {
                    "id": professor_id,
                    "count": count,
                    "courseFilter": course_filter,
                    "cursor": cursor,
                },
            },
        )
        response.raise_for_status()

        node = response.json()["data"]["node"]
        ratings_data = node["ratings"]
        page_info = ratings_data["pageInfo"]

        ratings = [
            Rating(
                id=edge["node"]["id"],
                legacy_id=edge["node"]["legacyId"],
                comment=edge["node"]["comment"],
                date=edge["node"]["date"],
                course=edge["node"]["class"],
                helpful_rating=edge["node"]["helpfulRating"],
                clarity_rating=edge["node"]["clarityRating"],
                difficulty_rating=edge["node"]["difficultyRating"],
                rating_tags=edge["node"]["ratingTags"],
                flag_status=edge["node"]["flagStatus"],
                attendance_mandatory=edge["node"]["attendanceMandatory"],
                would_take_again=edge["node"]["wouldTakeAgain"],
                grade=edge["node"]["grade"],
                textbook_use=edge["node"]["textbookUse"],
                is_for_online_class=edge["node"]["isForOnlineClass"],
                is_for_credit=edge["node"]["isForCredit"],
                thumbs_up_total=edge["node"]["thumbsUpTotal"],
                thumbs_down_total=edge["node"]["thumbsDownTotal"],
                teacher_note=edge["node"]["teacherNote"]["comment"]
                if edge["node"]["teacherNote"]
                else None,
            )
            for edge in ratings_data["edges"]
        ]

        return ratings, page_info["hasNextPage"], page_info["endCursor"]

    except Exception as e:
        print(f"Error fetching ratings: {e}")
        return [], False, None


def get_all_ratings(
    professor_id: str,
    course_filter: str | None = None,
    page_size: int = 20,
) -> list[Rating]:
    """Fetch ALL ratings for a professor, handling pagination automatically."""
    all_ratings = []
    cursor = None

    while True:
        ratings, has_next_page, cursor = get_ratings_page(
            professor_id,
            count=page_size,
            course_filter=course_filter,
            cursor=cursor,
        )
        all_ratings.extend(ratings)

        if not has_next_page:
            break

    return all_ratings


# --- Example usage ---
if __name__ == "__main__":
    schools = search_schools("University of California Berkeley")
    if schools:
        school_id = schools[0]["node"]["id"]

        results = search_professors("Jean Frechet", school_id)
        if results:
            professor_id = results[0]["node"]["id"]

            # Fetch one page of ratings
            ratings, has_next, end_cursor = get_ratings_page(professor_id, count=10)
            for r in ratings:
                print(r)

            # Or fetch every rating at once
            all_ratings = get_all_ratings(professor_id)
            print(f"Total ratings fetched: {len(all_ratings)}")
            
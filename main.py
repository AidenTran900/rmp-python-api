"""
main.py

api usage example for the RMP API wrapper.
"""


from client import search_schools, search_professors, get_ratings_page, get_all_ratings

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

import autoreply

# Safe local cases only
autoreply.run_demo()

# Include a live safe fetch
results = autoreply.run_demo(remote_url="https://api.github.com/repos/python/cpython")
print(results["remote_query"].detail)
print(results["remote_query"].executed)   # False — parsed only, nothing ran

# Direct fetch
repo = autoreply.query_dict(
    "https://api.github.com/repos/python/cpython",
    required_keys={"full_name", "stargazers_count"},
    headers={"User-Agent": "my-library/0.1"},
)
print(repo["full_name"], repo["stargazers_count"])

# All cases including unsafe fixtures (local study only)
autoreply.run_demo(include_unsafe=True)
<!DOCTYPE html>
<html>
<head>
    <title>PDF Keyword Search - DarwinSantiago</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .keyword-history { margin-bottom: 10px; }
        .keyword-history a {
            display: inline-block;
            background: #f0f0f0;
            padding: 5px 10px;
            margin: 2px;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
        }
        .result {
            margin-bottom: 10px;
            background: #e6f7ff;
            padding: 10px;
            border-left: 5px solid #1890ff;
        }
        .select-btn {
            margin-left: 10px;
            padding: 5px 10px;
            background: #1890ff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .select-btn:hover {
            background: #007acc;
        }
    </style>
</head>
<body>
    <h2>Upload a PDF & Search Keywords</h2>
    <form method="POST" enctype="multipart/form-data">
        <label><strong>PDF File:</strong></label>
        <input type="file" name="pdf_file" required><br><br>

        <label><strong>Keywords (comma-separated):</strong></label>
        <input type="text" name="keywords" id="keywords" placeholder="e.g., DWP, payment" required>
        <button type="button" class="select-btn" onclick="selectKeywords()">Select All</button>
        <button type="submit">Search</button>
    </form>

    {% if history %}
        <div class="keyword-history">
            <h4>Previously Searched Keywords:</h4>
            {% for kw in history %}
                <a href="#" onclick="addKeyword('{{ kw }}')">{{ kw }}</a>
            {% endfor %}
        </div>
    {% endif %}

    <hr>

    {% if results %}
        <h3>Search Results:</h3>
        {% for result in results %}
            <div class="result">{{ result }}</div>
        {% endfor %}
    {% elif keywords %}
        <p>No matches found for: <strong>{{ keywords|join(', ') }}</strong></p>
    {% endif %}

    <script>
        function addKeyword(kw) {
            let input = document.getElementById("keywords");
            if (!input.value.includes(kw)) {
                if (input.value.trim() !== "") {
                    input.value += "," + kw;
                } else {
                    input.value = kw;
                }
            }
        }

        function selectKeywords() {
            let input = document.getElementById("keywords");
            input.focus();
            input.select();
        }
    </script>
</body>
</html>

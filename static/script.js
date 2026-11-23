const resumeForm = document.getElementById("resumeForm");
const resumeInput = document.getElementById("resume");

resumeInput.addEventListener("change", () => {
    const file = resumeInput.files[0];

    if (file) {
        document.getElementById("fileTitle").textContent = file.name;
        document.getElementById("fileInfo").textContent = "Ready to analyze";
    }
});

resumeForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!resumeInput.files[0]) {
        alert("Please upload a resume first.");
        return;
    }

    const button = resumeForm.querySelector("button");
    const formData = new FormData();

    formData.append("resume", resumeInput.files[0]);

    formData.append(
        "job_description",
        document.getElementById("jobDescription").value
    );

    button.disabled = true;
    button.textContent = "Analyzing...";

    try {
        const response = await fetch(
            "/api/resume/analyze",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Analysis failed.");
        }

        document.getElementById("results")
            .classList.remove("hidden");

        document.getElementById("results")
            .scrollIntoView({ behavior: "smooth" });

        document.getElementById("score").textContent =
            data.score + "/100";

        document.getElementById("scoreBar").style.width =
            data.score + "%";

        document.getElementById("words").textContent =
            data.word_count;

        document.getElementById("skillCount").textContent =
            data.skills.length;

        const jobText =
            document.getElementById("jobDescription").value.trim();

        if (jobText) {
            const matchData = await matchJob(
                resumeInput.files[0],
                jobText
            );

            document.getElementById("jobScore").textContent =
                matchData.match_score + "%";

            document.getElementById("gaps").innerHTML =
                matchData.missing_skills.length
                ? matchData.missing_skills
                    .map(skill => chip(skill))
                    .join("")
                : "No relevant skill gaps detected.";
        } else {
            document.getElementById("jobScore").textContent = "—";
            document.getElementById("gaps").textContent =
                "Add a job description to calculate job match.";
        }

        document.getElementById("skills").innerHTML =
            data.skills.length
            ? data.skills.map(chip).join("")
            : "No common skills detected.";

        document.getElementById("sections").innerHTML =
            Object.entries(data.sections)
                .map(([name, found]) => `
                    <div class="row">
                        <span>${escapeHTML(name)}</span>
                        <b class="${found ? "ok" : "bad"}">
                            ${found ? "✓ Found" : "! Missing"}
                        </b>
                    </div>
                `)
                .join("");

        document.getElementById("suggestions").innerHTML =
            data.suggestions
                .map(item => `<li>${escapeHTML(item)}</li>`)
                .join("");

    } catch (error) {
        alert(error.message);
    } finally {
        button.disabled = false;
        button.textContent = "Analyze resume →";
    }
});

async function matchJob(file, job) {
    const formData = new FormData();

    formData.append("resume", file);
    formData.append("job_description", job);

    const response = await fetch(
        "/api/job/match",
        {
            method: "POST",
            body: formData
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Job matching failed.");
    }

    return data;
}

const questionButton =
    document.getElementById("questionButton");

questionButton.addEventListener("click", async () => {
    const file =
        document.getElementById("interviewFile").files[0];

    if (!file) {
        alert("Please upload your resume first.");
        return;
    }

    const formData = new FormData();
    formData.append("resume", file);

    questionButton.disabled = true;
    questionButton.textContent = "Reading resume...";

    try {
        const analysisResponse = await fetch(
            "/api/resume/analyze",
            {
                method: "POST",
                body: formData
            }
        );

        const analysis =
            await analysisResponse.json();

        if (!analysisResponse.ok) {
            throw new Error(analysis.error);
        }

        const response = await fetch(
            "/api/interview/question",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    resume_text: JSON.stringify(analysis),
                    type: document.getElementById(
                        "interviewType"
                    ).value
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error);
        }

        window.currentQuestion = data.question;

        document.getElementById("question").textContent =
            data.question;

        document.getElementById("questionArea")
            .classList.remove("hidden");

    } catch (error) {
        alert(error.message);
    } finally {
        questionButton.disabled = false;
        questionButton.textContent = "Generate question";
    }
});

document.getElementById("evaluateButton")
    .addEventListener("click", async () => {

        const answer =
            document.getElementById("answer").value.trim();

        if (!answer) {
            alert("Please write your answer.");
            return;
        }

        const response = await fetch(
            "/api/interview/evaluate",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    question: window.currentQuestion,
                    answer: answer
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            alert(data.error);
            return;
        }

        document.getElementById("feedback").innerHTML = `
            <div class="panel">
                <h3>Score: ${data.score}/10</h3>

                <p>
                    Technical:
                    ${data.technical_score}/10
                    &nbsp; · &nbsp;
                    Communication:
                    ${data.communication_score}/10
                </p>

                <h4>Strengths</h4>
                <ul>
                    ${data.strengths
                        .map(x => `<li>${escapeHTML(x)}</li>`)
                        .join("")}
                </ul>

                <h4>Improvements</h4>
                <ul>
                    ${data.improvements
                        .map(x => `<li>${escapeHTML(x)}</li>`)
                        .join("")}
                </ul>

                <p>
                    <b>Better approach:</b>
                    ${escapeHTML(data.better_approach)}
                </p>
            </div>
        `;
    });

function chip(value) {
    return `<span class="chip">${escapeHTML(value)}</span>`;
}

function escapeHTML(value) {
    return String(value).replace(
        /[&<>"']/g,
        char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[char]
    );
}

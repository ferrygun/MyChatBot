const express = require("express");
const path = require("path");
const fetch = require("node-fetch"); // Add the fetch library
const app = express();
const port = 3000;

app.use(express.static(path.join(__dirname, "public")));

// Define an endpoint to handle sending and receiving messages
app.post("/sendMessage", express.json(), async (req, res) => {
    let userMessage = req.body;
    console.log("userMessage: ");
    console.log(userMessage)


    // Send user's message to the backend API to get a reply
    const apiUrl = "http://localhost:8000/ask"; // Replace with your actual API URL
    const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({userMessage }),
    });

    console.log(response)

    if (response.ok) {
        const data = await response.json();
        console.log(data);
        const botReply = data;

        // You can modify the structure and content of the reply as needed
        res.json({ reply: botReply });
    } else {
        res.status(response.status).json({ error: "Error fetching response from API" });
    }
});

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

const chatBox = document.getElementById("chatBox");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

const randomString = generateRandomString(5);
sendButton.addEventListener("click", sendMessage);

function generateRandomString(length) {
  const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";
  
  for (let i = 0; i < length; i++) {
    const randomIndex = Math.floor(Math.random() * charset.length);
    result += charset.charAt(randomIndex);
  }
  
  return result;
}


function sendMessage() {
    const message = messageInput.value;
    if (message.trim() !== "") {
        displayMessage(message, "You");


        // Send the user's message to the server
        fetch("/sendMessage", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({user_id: randomString, question: message }),
        })
        .then(response => response.json())
        .then(data => {
            let botReply = data
            //botReply = botReply.answer;

            console.log(botReply);
            console.log("Answer from bot:");
            console.log(botReply.reply);

            displayMessage(botReply.reply.answer, "Bot");
        })
        .catch(error => {
            console.error("Error sending message:", error);
        });

        messageInput.value = "";
    }
}



function displayMessage(message, isUser) {
    const messageElement = document.createElement("div");
    messageElement.classList.add("message");
    
    if (isUser === "You") {
        messageElement.innerHTML = "<br><b>You:</b> " + message ;
    } else {
        messageElement.innerHTML = "<br><b>Bot:</b> " + message;
    }
    
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
}

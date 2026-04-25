const BASE_URL = "https://agentic-ai-receptionist.onrender.com";

export async function bookAppointment(data) {
  const res = await fetch(`${BASE_URL}/book-appointment`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return res.json();
}
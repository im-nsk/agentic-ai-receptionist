import { useState } from "react";
import { bookAppointment } from "../api/client";

export default function Dashboard() {
  const [form, setForm] = useState({
    client_id: "",
    name: "",
    phone: "",
    date: "",
    time: "",
  });

  const handleSubmit = async () => {
    const res = await bookAppointment(form);
    alert(JSON.stringify(res));
  };

  return (
    <div>
      <h2>Book Appointment</h2>

      <input placeholder="Client ID" onChange={(e) => setForm({...form, client_id: e.target.value})} />
      <input placeholder="Name" onChange={(e) => setForm({...form, name: e.target.value})} />
      <input placeholder="Phone" onChange={(e) => setForm({...form, phone: e.target.value})} />
      <input placeholder="Date (tomorrow / April 25)" onChange={(e) => setForm({...form, date: e.target.value})} />
      <input placeholder="Time (10 AM)" onChange={(e) => setForm({...form, time: e.target.value})} />

      <button onClick={handleSubmit}>Book</button>
    </div>
  );
}
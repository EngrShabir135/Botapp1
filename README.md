# 🧠 Business Sense IT — Bot Dashboard

A **production-style Streamlit dashboard** showcasing a **multi-bot management system** with roles, task scheduling, simulated web search, and local data storage.

This proof-of-concept (POC) demonstrates how an IT automation bot dashboard could look and behave — designed for business intelligence, task orchestration, and background automation simulation.

---

## 🚀 Features

✅ **Multi-Bot Management**
- Create, edit, and delete bots  
- Assign multiple roles to each bot  

✅ **Role System**
- Create reusable roles across bots  
- Store and manage in SQLite  

✅ **Task Scheduling**
- Queue or schedule tasks (immediate or delayed)  
- Background worker thread simulates execution  

✅ **Simulated Internet Search**
- Multi-engine (Google, Bing, DuckDuckGo, Yahoo) mock search  
- Saves results to local files under `~/.biz_sense_bot/internet_information/`  

✅ **Advertising / Image Simulation**
- Generates placeholder text files simulating ad/image creation  

✅ **Browser & App Launch Simulation**
- Simulates launching browsers or desktop apps safely  

✅ **Secure Login**
- Default password: `admin123` (changeable in code)  

✅ **Snapshot & Logging**
- Export database and logs as a `.zip` snapshot  
- Activity logs stored at `~/.biz_sense_bot/activity.log`

✅ **Responsive UI**
- Modern Streamlit layout  
- Light/Dark gradient cards  
- Works on desktop and mobile  

---

## 🗂️ Project Structure


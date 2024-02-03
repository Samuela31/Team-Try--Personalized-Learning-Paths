import streamlit as st
import pandas as pd
import mysql.connector
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from model import df  
from model import train_stacking_model
from model import get_recommendations 
from bot import gemini

#Background image
page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
background-image: url("https://png.pngtree.com/background/20220714/original/pngtree-blue-pastel-background-with-leaves-ornament-picture-image_1603840.jpg");
background-size: cover;
background-position: center center;
background-repeat: no-repeat;
background-attachment: local;
}}
[data-testid="stHeader"] {{
background: rgba(0,0,0,0);
}}
</style>
"""
   
#Function to connect to MySQL and fetch unique student IDs
def get_unique_student_ids():
   # Access database credentials using st.secrets
   db_credentials = st.secrets["connections.mysql"]
   
   # Establish a connection to the MySQL database
   connection = mysql.connector.connect(
       host=db_credentials["host"],
       user=db_credentials["username"],
       password=db_credentials["password"],
       database=db_credentials["database"]
   )

    cursor = connection.cursor(dictionary=True)

    #Fetch unique student IDs from the database
    query = "SELECT DISTINCT ID FROM pl_student_data"
    cursor.execute(query)
    unique_student_ids = [result['ID'] for result in cursor.fetchall()]

    connection.close()
    return unique_student_ids

#Function to connect to MySQL and fetch student details
def get_student_details(student_id):
   # Access database credentials using st.secrets
   db_credentials = st.secrets["connections.mysql"]
   
   # Establish a connection to the MySQL database
   connection = mysql.connector.connect(
       host=db_credentials["host"],
       user=db_credentials["username"],
       password=db_credentials["password"],
       database=db_credentials["database"]
   )

    cursor = connection.cursor(dictionary=True)

    #Fetch student details based on ID
    query = f"SELECT * FROM pl_student_data WHERE ID = '{student_id}'"
    cursor.execute(query)
    student_data = cursor.fetchone()

    connection.close()
    return student_data

#Function to connect to MySQL and fetch activities data for a specific student
def get_student_activities(student_id):
   # Access database credentials using st.secrets
   db_credentials = st.secrets["connections.mysql"]
   
   # Establish a connection to the MySQL database
   connection = mysql.connector.connect(
       host=db_credentials["host"],
       user=db_credentials["username"],
       password=db_credentials["password"],
       database=db_credentials["database"]
   )
    cursor = connection.cursor(dictionary=True)

    #Fetch activities data based on student ID
    query = f"SELECT * FROM activities_finished_data WHERE sid = '{student_id}'"
    cursor.execute(query)
    activities_data = cursor.fetchall()

    connection.close()
    return activities_data

#Function to update the MySQL database on completion of activity
def update_database(student_id, attribute_column):
   # Access database credentials using st.secrets
   db_credentials = st.secrets["connections.mysql"]
   
   # Establish a connection to the MySQL database
   connection = mysql.connector.connect(
       host=db_credentials["host"],
       user=db_credentials["username"],
       password=db_credentials["password"],
       database=db_credentials["database"]
   )

    cursor = connection.cursor()
    
    #Enclose column name in backticks
    column_name_with_backticks = f"`{attribute_column}`"
    
    query = f"UPDATE pl_student_data SET {column_name_with_backticks} = 1 WHERE ID = '{student_id}'"

    try:
        cursor.execute(query)
        connection.commit()
        st.success(f"Updated {attribute_column} for student {student_id}")
    except mysql.connector.Error as err:
        st.error(f"Error updating database: {err}")

    connection.close()    

#Function to update the MySQL database on completion of assessments and quizes
def update_database_aq(student_id, attribute_column, score):
   # Access database credentials using st.secrets
   db_credentials = st.secrets["connections.mysql"]
   
   # Establish a connection to the MySQL database
   connection = mysql.connector.connect(
       host=db_credentials["host"],
       user=db_credentials["username"],
       password=db_credentials["password"],
       database=db_credentials["database"]
   )

    cursor = connection.cursor()
    
    #Enclose column name in backticks
    column_name_with_backticks = f"`{attribute_column}`"
    
    query = f"UPDATE pl_student_data SET {column_name_with_backticks} = {score} WHERE ID = '{student_id}' AND {column_name_with_backticks} = 0"

    try:
        cursor.execute(query)
        connection.commit()
        st.success(f"Updated {attribute_column} for student {student_id}")
    except mysql.connector.Error as err:
        st.error(f"Error updating database: {err}")

    connection.close()    

#Form and evaluation for assessments
def display_assessment(questions_and_answers, form_key):
    user_responses, question_list = [], []

    #Create a form for the assessment
    form = st.form(key=form_key)

    #Iterate through each question and add a text box for the answer
    for i, (question, correct_answer) in enumerate(questions_and_answers):
        with form:
            st.markdown(f"**Question {i + 1}:** {question}")
            user_answer = st.text_input(f"Your Answer for Question {i + 1}")

            #Collect student responses in a list
            user_responses.append((user_answer, correct_answer))
            question_list.append(question)

    #When submit button is clicked
    if form.form_submit_button(label="Submit"):
        #Verify answers after the submit button is clicked
        incorrect_questions, incorrect_responses = verify_answers(user_responses, question_list)

        #Display the result
        correct_answers_count = len(questions_and_answers) - len(incorrect_questions)
        st.write(f"You got {correct_answers_count} out of {len(questions_and_answers)} questions correct.")
        score=correct_answers_count*25 #Assuming assessment has 4 questions each of 25 marks (max total score=100)

        if incorrect_questions:
            st.subheader("Incorrect Questions:")
            for i, (user_answer, correct_answer) in enumerate(incorrect_responses):
                st.write(f"{i + 1}. Your answer: {user_answer}, Correct answer: {correct_answer}")
        else:
            st.success("Congratulations! All answers are correct.")

        return incorrect_questions, incorrect_responses, score  

    return [], [], 0  #Return an empty list if the submit button is not clicked

def verify_answers(user_responses, question_list):
    incorrect_questions, incorrect_responses, i = [], [], 0

    #Verify each answer
    for user_answer, correct_answer in user_responses:
        if not verify_answer(user_answer, correct_answer):
            incorrect_responses.append((user_answer, correct_answer))
            incorrect_questions.append(question_list[i])
        i += 1

    return incorrect_questions, incorrect_responses

def verify_answer(user_answer, correct_answer):
    #Compare the user's answer with the correct answer
    return user_answer.lower() == correct_answer.lower()

def create_quiz(quiz_data, quiz_key):
    user_responses, question_list = [], []

    #Display questions and collect user responses
    for i, question_data in enumerate(quiz_data):
        st.markdown(f"**Question {i + 1}:** {question_data['question']}")
        user_answer = st.radio(f"Select your answer for Question {i + 1}:", question_data['options'])
        user_responses.append((user_answer, question_data['correct_answer']))
        question_list.append(question_data['question'])

    #Use a single submit button for the entire quiz
    if st.button("Submit", key=quiz_key):
        #Verify answers after the submit button is clicked
        st.subheader("Quiz Results")
    
        correct_count = 0
        incorrect_questions, incorrect_responses = [], []

        #Verify each answer and display results
        for i, (user_answer, correct_answer) in enumerate(user_responses):
            if user_answer == correct_answer:
                correct_count += 1
            else:
                st.markdown(f"**You got Question {i + 1} wrong:** Your answer: {user_answer}, Correct answer: {correct_answer}")
                incorrect_questions.append(question_list[i])
                incorrect_responses.append((user_answer, correct_answer))

        #Display overall score
        st.write(f"You got {correct_count} out of {len(quiz_data)} questions correct.")
        score=correct_count*12.5 #Assuming quiz has 2 questions each of 12.5 marks (max total score=25)
        if len(incorrect_questions)==0:
            st.success("Congratulations! All answers are correct.")

        return incorrect_questions, incorrect_responses, score

    return [], [], 0

#Use st.@st.cache_resource to cache the model to reduce time for loading pages
@st.cache_resource
def load_model():
    return train_stacking_model()

@st.cache_resource
def load_model2(student_row):
    return get_recommendations(student_row)

@st.cache_resource
def load_model3(prompt):
    return gemini(prompt)

#Login page 
def login():
    lpage_bg_img = f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
    background-image: url("https://wallpapercave.com/wp/wp1895390.jpg");
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    background-attachment: local;
    }}
    [data-testid="stHeader"] {{
    background: rgba(0,0,0,0);
    }}
    </style>
    """
    st.markdown(lpage_bg_img, unsafe_allow_html=True)

    st.title("Login Page")

    #Input fields for username and password
    username = st.text_input("ID")
    password = st.text_input("Password", type="password")

    #Get unique student IDs from the database
    available_ids = get_unique_student_ids()

    #Login button
    if st.button("Login"):
        #Check if entered credentials are valid
        if username in available_ids:
            student_details = get_student_details(username) #Get student details based on input ID

            if password == student_details['Password']:
                st.session_state.student_details = student_details # Save student_details in session_state
                st.success("Login successful!")
                st.session_state.page = "home" #Go to main page on successful login

            else:
                st.error("Invalid username or password")

def main_page():
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.title("Student Portal")

    #Access student_details from session_state
    student_details = st.session_state.student_details

    st.subheader(f"Welcome, {student_details['Name']}!") 

    #Map column names to the specified order
    new_colnames = [
        'ID', 'Name', 'Learning preference', 'Assessment 1', 'Assessment 2', 'Quiz 1', 'Quiz 2',
        'Beginner lecture 1', 'Beginner lecture 2', 'Beginner lecture 3',
        'Medium lecture 1', 'Medium lecture 2', 'Medium lecture 3',
        'Advanced lecture 1', 'Advanced lecture 2', 'Advanced lecture 3',
        'Beginner lesson 1', 'Beginner lesson 2', 'Beginner lesson 3',
        'Medium lesson 1', 'Medium lesson 2', 'Medium lesson 3',
        'Advanced lesson 1', 'Advanced lesson 2', 'Advanced lesson 3',
        'Beginner hands-on 1', 'Beginner hands-on 2', 'Beginner hands-on 3',
        'Medium hands-on 1', 'Medium hands-on 2', 'Medium hands-on 3',
        'Advanced hands-on 1', 'Advanced hands-on 2', 'Advanced hands-on 3',
        'Overall Score', 'Overall Performance', 'Password'
    ]

    old_colnames = [
        'ID', 'Name', 'Learning_preference', 'Assessment_1', 'Assessment_2', 'Quiz_1', 'Quiz_2',
        'Beginner_lecture_1', 'Beginner_lecture_2', 'Beginner_lecture_3',
        'Medium_lecture_1', 'Medium_lecture_2', 'Medium_lecture_3',
        'Advanced_lecture_1', 'Advanced_lecture_2', 'Advanced_lecture_3',
        'Beginner_lesson_1', 'Beginner_lesson_2', 'Beginner_lesson_3',
        'Medium_lesson_1', 'Medium_lesson_2', 'Medium_lesson_3',
        'Advanced_lesson_1', 'Advanced_lesson_2', 'Advanced_lesson_3',
        'Beginner_hands_on_1', 'Beginner_hands_on_2', 'Beginner_hands_on_3',
        'Medium_hands_on_1', 'Medium_hands_on_2', 'Medium_hands_on_3',
        'Advanced_hands_on_1', 'Advanced_hands_on_2', 'Advanced_hands_on_3',
        'Overall_Score', 'Overall_Performance', 'Password'
    ]

    #Create a DataFrame with a single row (index=[0])
    input_data = pd.DataFrame(student_details, index=[0])
    column_mapping = dict(zip(old_colnames, new_colnames))
    input_data.rename(columns=column_mapping, inplace=True)

    st.session_state.student_row = input_data
    stacking_model = load_model()
    learning_style_prediction = stacking_model.predict(input_data.iloc[:, 7:-3])

    st.session_state.learning_style = learning_style_prediction[0]
    #Define personalized messages based on the learning style
    prompt= f"Give tips and study methods to me having a learning style {learning_style_prediction[0]}"
    message=load_model3(prompt)

    #Formatting prediction result in bold text
    formatted_prediction = f"**{learning_style_prediction[0]}**"

    #Displaying formatted prediction in a green box
    st.success(f"Your predicted learning style based on your activities is: {formatted_prediction} \n \n Some tips for you: \n {message}")

    st.write("Start your learning journey! Go to:")

    #Buttons to navigate to other pages
    col1, col2, col3 = st.columns(3)
    if col1.button("Dashboard"):
        st.session_state.page = "page1"

    if col2.button("Study"):
        st.session_state.page = "page2"

    if col3.button("Assessments and Quizes"):
        st.session_state.page = "page3"

def page1():
    st.markdown(page_bg_img, unsafe_allow_html=True)

    #Access student_details from session_state
    student_details = st.session_state.student_details
    
    #Button to go back to the home page
    if st.button("Go back to Home Page"):
        st.session_state.page = "home"
    
    st.title("Dashboard")
    st.subheader("Your progress over time: ")

    #Get activities data for the specified student
    activities_data = get_student_activities(student_details["ID"])

    if not activities_data:
        st.warning("You haven't started any activities so far. Go to study portal to start doing activities!")
    else:
        #Convert activities data to a pandas DataFrame
        df_activities = pd.DataFrame(activities_data)
        df_activities['finish_date'] = pd.to_datetime(df_activities['finish_date'])

        #Count the number of activities finished on each date
        activity_counts = df_activities.groupby('finish_date').size().reset_index(name='count')

        #Line graph
        fig, ax = plt.subplots()
        ax.plot(activity_counts['finish_date'], activity_counts['count'], marker='o', linestyle='-')

        #Format the x-axis dates
        ax.xaxis.set_major_locator(mdates.DayLocator())  
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))  #Format as day and abbreviated month

        ax.set_xlabel('Date')
        ax.set_ylabel('Number of Activities Finished')
        ax.set_title('Activities Finished Over Time')

        plt.xticks(rotation=45)  #Rotate x-axis labels for better readability
        plt.tight_layout()
        st.pyplot(fig)

        prompt= f"Comment on my progress and give feedback or motivation based on my progress of activity completion over the days: {activities_data}"
        message=load_model3(prompt)
        st.success(f"**Feedback based on your Progress:** \n \n {message}")

    #Getting values from student ID's record
    completion_data = [student_details[col] for col in student_details]

    #Give warning for tasks whose scores are 0
    s,j=' ',0
    t=['Assessment 1', 'Assessment 2', 'Quiz 1', 'Quiz 2']
    for i in range(3,7):
        if completion_data[i]==0:
            s=s+t[j]+', '

        j=j+1

    st.subheader("Your completion status of Assessments and Quizzes: ")

    if 0 in completion_data[3:7]:
        st.warning(f"Your score for {s}is 0. Please complete them under Assesssments and Quizes portal to get your score.")

    #Plot bargraphs for assessments and quizes
    fig, ax = plt.subplots(1, 2, figsize=(8, 5))

    #Bargraph for assessments
    student_scores = completion_data[3:5]
    class_averages = [df.iloc[:, 3].mean(), df.iloc[:, 4].mean()]

    bars1 = ax[0].bar(['Assessment 1', 'Assessment 2'], student_scores, color='green')
    bars2 = ax[0].bar(['Assessment 1', 'Assessment 2'], class_averages, color='orange')
    ax[0].set_ylim(0, 100)
    ax[0].set_ylabel('Score')
    ax[0].set_title('Assessment Scores')
    ax[0].legend(['Your Score', 'Class Average'])

    #Display scores on top of bars
    for bar, score in zip(bars1, student_scores):
        ax[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(score),
                ha='center', va='bottom', color='black')

    for bar, score in zip(bars2, class_averages):
        ax[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(score),
                ha='center', va='bottom', color='black')

    #Bargraph for quizzes
    student_scores = completion_data[5:7]
    class_averages = [df.iloc[:, 5].mean(), df.iloc[:, 6].mean()]

    bars3 = ax[1].bar(['Quiz 1', 'Quiz 2'], student_scores, color='pink')
    bars4 = ax[1].bar(['Quiz 1', 'Quiz 2'], class_averages, color='yellow')
    ax[1].set_ylim(0, 25)
    ax[1].set_ylabel('Score')
    ax[1].set_title('Quiz Scores')
    ax[1].legend(['Your Score', 'Class Average'])

    #Display scores on top of bars
    for bar, score in zip(bars3, student_scores):
        ax[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(score),
                ha='center', va='bottom', color='black')

    for bar, score in zip(bars4, class_averages):
        ax[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(score),
                ha='center', va='bottom', color='black')

    plt.tight_layout()
    st.pyplot(fig)

    #Plotting pie charts for completion status of lectures, lessons, hands-ons
    st.subheader("Your completion status of Activities: ")

    #Calculate percentage completed for lectures
    completed_count = sum(completion_data[7:16])
    total_activities = len(completion_data[7:16])
    lc_percentage_completed = (completed_count / total_activities) * 100

    data1 = {'Completion Status': ['Completed', 'Not Completed'], 'Percentage': [lc_percentage_completed, 100 - lc_percentage_completed]}

    #Calculate percentage completed for lessons
    completed_count = sum(completion_data[16:25])
    total_activities = len(completion_data[16:25])
    ls_percentage_completed = (completed_count / total_activities) * 100

    data2 = {'Completion Status': ['Completed', 'Not Completed'], 'Percentage': [ls_percentage_completed, 100 - ls_percentage_completed]}

    #Calculate percentage completed for hands-ons
    completed_count = sum(completion_data[25:34])
    total_activities = len(completion_data[25:34])
    h_percentage_completed = (completed_count / total_activities) * 100

    data3 = {'Completion Status': ['Completed', 'Not Completed'], 'Percentage': [h_percentage_completed, 100 - h_percentage_completed]}

    #Using single Matplotlib figure with three subplots
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))

    #Define colors for 'Completed' and 'Not Completed'
    colors = ['#33FF36', '#FFCA33']

    #Plot the first pie chart
    axs[0].pie(data1['Percentage'], labels=data1['Completion Status'], autopct='%1.1f%%', startangle=90, colors=colors)
    axs[0].set_title('Completion Status of Lectures')

    #Plot the second pie chart
    axs[1].pie(data2['Percentage'], labels=data2['Completion Status'], autopct='%1.1f%%', startangle=90, colors=colors)
    axs[1].set_title('Completion Status of Lessons')

    #Plot the third pie chart
    axs[2].pie(data3['Percentage'], labels=data3['Completion Status'], autopct='%1.1f%%', startangle=90, colors=colors)
    axs[2].set_title('Completion Status of Hands-on Acivities')

    plt.tight_layout()
    st.pyplot(fig)

    st.subheader("Leaderboard (based on Overall Score):")

    #Create a new DataFrame for the current student
    student_df = pd.DataFrame(student_details, index=[0])

    #Concatenate the new DataFrame with the original DataFrame
    df_extended = pd.concat([df, student_df], ignore_index=True)

    #Sort the DataFrame by Overall Score
    df_sorted = df_extended.sort_values(by='Overall Score', ascending=False)

    #Sort the DataFrame by Overall Score and get the top 10
    top_10_students = df_sorted.head(10)
    top_10_students['Rank'] = range(1, 11)

    #Check if Overall Score is 0 for the current student
    if student_details["Overall_Score"]==0:
        st.table(top_10_students[['Rank', 'Name', 'Overall Score']])
        st.warning("Your Overall Score is 0. Please complete assessments and quizzes to get your Overall Score.")

    #Check if the student is in the top 10
    elif student_details["ID"] in top_10_students["ID"].values:
        st.table(top_10_students[['Rank', 'Name', 'Overall Score']])
    else:
        st.table(top_10_students[['Rank', 'Name', 'Overall Score']])

        #Find the rank of the current student
        rank = df_sorted[df_sorted['ID'] == student_details['ID']].index[0] + 1

        #Display the row with '....' to signify that previous rows are top 10
        st.table(pd.DataFrame({"Rank": ["...."], "Name": ["...."], "Overall Score": ["...."]}))
        
        #Display the current student's name, score, and rank
        st.table(pd.DataFrame({"Rank": [rank], "Name": [student_details["Name"]], "Overall Score": [student_details["Overall_Score"]]}))

    #Define personalized messages based on the learning style and progress
    ls = st.session_state.learning_style
    prompt= f"Give inference and encouragement to me based on completion status percentage of {lc_percentage_completed},{ls_percentage_completed},{h_percentage_completed} for lectures, lessons, and hands-on activities respectively with a learning style of {ls} and score of {student_details['Assessment_1']},{student_details['Assessment_2']},{student_details['Quiz_1']},{student_details['Quiz_2']} in assessments and quizes. If any score is 0 it means either I haven't attempted it yet or indeed I'm very poor in studies."
    message=load_model3(prompt)
    st.success(f"**Did you know?** \n \n {message}")    

def page2():
    st.markdown(page_bg_img, unsafe_allow_html=True)

    #Access student_details from session_state
    student_details = st.session_state.student_details
    
    #Button to go back to the home page
    if st.button("Go back to Home Page"):
        st.session_state.page = "home"

    st.title("Activities Portal")
    st.subheader("Your Recommended Activities")

    input_data = st.session_state.student_row
    pl_path, pl_students = load_model2(input_data.iloc[0])

    #Filter Beginner activities from pl_path
    beginner_activities = [activity for activity in pl_path if "Beginner" in activity]

    #Create a DataFrame for Beginner activities
    beginner_df = pd.DataFrame({"Recommended Activities": beginner_activities})

    #Add a "Status" column to the DataFrame
    beginner_df["Status"] = beginner_df["Recommended Activities"].apply(
        lambda activity: "Completed" if input_data[activity].values[0] == 1 else "Pending"
    )

    #Apply text color using HTML
    styled_df = beginner_df.style.apply(
        lambda x: ["color: green" if val == "Completed" else "color: blue" for val in x],
        subset=["Status"]
    )

    #Medium activities
    medium_activities = [activity for activity in pl_path if "Medium" in activity]
    medium_df = pd.DataFrame({"Recommended Activities": medium_activities})

    medium_df["Status"] = medium_df["Recommended Activities"].apply(
        lambda activity: "Completed" if input_data[activity].values[0] == 1 else "Pending"
    )

    mstyled_df = medium_df.style.apply(
        lambda x: ["color: green" if val == "Completed" else "color: blue" for val in x],
        subset=["Status"]
    )

    #Advanced activities
    advanced_activities = [activity for activity in pl_path if "Advanced" in activity]
    advanced_df = pd.DataFrame({"Recommended Activities": advanced_activities})

    advanced_df["Status"] = advanced_df["Recommended Activities"].apply(
        lambda activity: "Completed" if input_data[activity].values[0] == 1 else "Pending"
    )

    astyled_df = advanced_df.style.apply(
        lambda x: ["color: green" if val == "Completed" else "color: blue" for val in x],
        subset=["Status"]
    )

    col1, col2 = st.columns(2)
    col1.write("Beginner activities:")
    col1.write(styled_df)
    col1.write("Advanced activities:")
    col1.write(astyled_df)

    col2.write("Medium activities:")
    col2.write(mstyled_df)
    
    st.write("Recommended Students to Study with:")

    pl_students_df = pd.DataFrame(pl_students, columns=['ID'])

    #Merge the two DataFrames on the 'ID' column
    merged_df = pd.merge(pl_students_df, df, on='ID', how='inner')
    rdf= merged_df.iloc[:, 0:2]

    #Function to set table background color
    def set_background_color(val):
        return 'background-color: white'

    styled_df = rdf.style.applymap(set_background_color)
    st.table(styled_df)

    activities_columns = input_data.columns[7:34]

    #Create a grid to display buttons
    button_grid = st.container()

    #Iterate over columns and display buttons
    with button_grid:
        st.header("Complete Remaining Activities:")

        for column in activities_columns:
            if input_data[column].values[0] == 0:
                #Display a button for columns with value 0
                if st.button(column):
                    prompt= f"I just completed activity {column}. Recommend 3 activities to do next based on my current level from this list: {pl_path}"
                    message=load_model3(prompt)
                    st.success(f"**Recommended Activities to do next:** \n \n {message}")

                    #Get the column index based on the column name
                    column_index = input_data.columns.get_loc(column)

                    keys_list = list(student_details.keys())

                    #Mark activity as completed when the button is clicked
                    update_database(student_details['ID'], keys_list[column_index])

        st.header("Completed Activities:")

        for column in activities_columns:
            if input_data[column].values[0] == 1:
                #Display a button for columns with value 1
                if st.button(column):
                    #Perform an action when the button is clicked
                    st.write(f"{column} already completed!")            
 
def page3():
    st.markdown(page_bg_img, unsafe_allow_html=True)

    #Access student_details from session_state
    student_details = st.session_state.student_details
    
    #Button to go back to the home page
    if st.button("Go back to Home Page"):
        st.session_state.page = "home"

    st.title("Assessments and Quizes")
    st.subheader("Assessments")
    st.write("Assessment 1")

    questions_and_answers = [
    ("While moving down in a group, what happens to the metallic character in periodic table?", "Increases"),
    ("What is the maximum number of electrons that can accommodate in a k shell?", "2"),
    ("Write the balanced chemical equation for electrolysis of water", "2H2O -> 2H2 + O2"),
    ("Is copper a good conductor of electricity?", "Yes")
    ]

    incorrect_questions, incorrect_responses, score = display_assessment(questions_and_answers, 'assessment_form')

    if score!=0:
        #Update score in database
        update_database_aq(student_details['ID'], 'Assessment_1', score)

    if len(incorrect_questions) != 0:
        #Give personalized feedback based on performance
        prompt = f"Identify my weakness based on the following questions which I answered incorrectly: {incorrect_questions}. This list contains sets of my answer and correct answer for corresponding questions {incorrect_responses}"
        message=load_model3(prompt)
        prompt1 = f"Give simple step-by-step solution or explanation to the following questions which I answered incorrectly: {incorrect_questions}. This list contains sets of my answer and correct answer for corresponding questions {incorrect_responses}"
        message1=load_model3(prompt1)
        prompt2 = f"Suggest practice questions based on the following questions which I answered incorrectly: {incorrect_questions}"
        message2=load_model3(prompt2)
        st.success(f"**Feedback and More Questions for Practice** \n \n {message} \n {message1} \n {message2}")       

    st.write("Assessment 2")

    questions_and_answers2 = [
    ("Which gas is responsible for the greenhouse effect on Earth?", "Carbon dioxide"),
    ("What is the chemical symbol for gold?", "Au"),
    ("In the human body, which organ produces insulin?", "Pancreas"),
    ("What is the primary function of mitochondria?", "Produce energy"),
    ]

    incorrect_questions2, incorrect_responses2, score2 = display_assessment(questions_and_answers2, 'assessment_form2')

    if score2!=0:
        #Update score in database
        update_database_aq(student_details['ID'], 'Assessment_2', score2)

    if len(incorrect_questions2) != 0:
        #Give personalized feedback based on performance
        prompt = f"Identify my weakness based on the following questions which I answered incorrectly: {incorrect_questions2}. This list contains sets of my answer and correct answer for corresponding questions {incorrect_responses2}"
        message=load_model3(prompt)
        prompt1 = f"Give simple step-by-step solution or explanation to the following questions which I answered incorrectly: {incorrect_questions2}. This list contains sets of my answer and correct answer for corresponding questions {incorrect_responses2}"
        message1=load_model3(prompt1)
        prompt2 = f"Suggest practice questions based on the following questions which I answered incorrectly: {incorrect_questions2}"
        message2=load_model3(prompt2)
        st.success(f"**Feedback and More Questions for Practice** \n \n {message} \n {message1} \n {message2}")

    st.subheader("Quizes")
    st.write("Quiz 1")

    quiz_data = [
    {
        "question": "What is the capital of France?",
        "options": ["London", "Paris", "Berlin", "Madrid"],
        "correct_answer": "Paris",
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Mars", "Jupiter", "Venus", "Saturn"],
        "correct_answer": "Mars",
    },
    ]

    qincorrect_questions, qincorrect_responses, qscore = create_quiz(quiz_data, 'quiz_key')

    if qscore!=0:
        #Update score in database
        update_database_aq(student_details['ID'], 'Quiz_1', qscore)

    if len(qincorrect_questions) != 0:
        #Give personalized feedback based on performance
        prompt = f"Identify my weakness based on the following questions which I answered incorrectly: {qincorrect_questions}. This list contains sets of my answer and correct answer for corresponding questions {qincorrect_responses}"
        message=load_model3(prompt)
        prompt1 = f"Give simple step-by-step solution or explanation to the following questions which I answered incorrectly: {qincorrect_questions}. This list contains sets of my answer and correct answer for corresponding questions {qincorrect_responses}"
        message1=load_model3(prompt1)
        prompt2 = f"Suggest practice questions based on the following questions which I answered incorrectly: {qincorrect_questions}"
        message2=load_model3(prompt2)
        st.success(f"**Feedback and More Questions for Practice** \n \n {message} \n {message1} \n {message2}")  

    st.write("Quiz 2")

    quiz_data2 = [
        {
            "question": "What is the capital of Italy?",
            "options": ["Rome", "Paris", "Berlin", "Madrid"],
            "correct_answer": "Rome",
        },
        {
            "question": "Which planet is known as the Blue Planet?",
            "options": ["Earth", "Mars", "Venus", "Saturn"],
            "correct_answer": "Earth",
        },
    ]

    qincorrect_questions2, qincorrect_responses2, qscore2 = create_quiz(quiz_data2, 'quiz_key2')

    if qscore2!=0:
        #Update score in database
        update_database_aq(student_details['ID'], 'Quiz_2', qscore2)

    if len(qincorrect_questions2) != 0:
        #Give personalized feedback based on performance
        prompt = f"Identify my weakness based on the following questions which I answered incorrectly: {qincorrect_questions2}. This list contains sets of my answer and correct answer for corresponding questions {qincorrect_responses2}"
        message=load_model3(prompt)
        prompt1 = f"Give simple step-by-step solution or explanation to the following questions which I answered incorrectly: {qincorrect_questions2}. This list contains sets of my answer and correct answer for corresponding questions {qincorrect_responses2}"
        message1=load_model3(prompt1)
        prompt2 = f"Suggest practice questions based on the following questions which I answered incorrectly: {qincorrect_questions2}"
        message2=load_model3(prompt2)
        st.success(f"**Feedback and More Questions for Practice** \n \n {message} \n {message1} \n {message2}")  

#Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "login"

#Display content based on the current page
if st.session_state.page == "login":
    login()
elif st.session_state.page == "home":
    main_page()
elif st.session_state.page == "page1":
    page1()
elif st.session_state.page == "page2":
    page2()
elif st.session_state.page == "page3":
    page3()

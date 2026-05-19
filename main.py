from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# بيانات بسيطة
X = [
    [25, 50000],
    [30, 60000],
    [45, 80000],
    [35, 120000],
    [22, 20000],
    [40, 95000]
]

# Labels
y = [0, 0, 1, 1, 0, 1]

# تقسيم الداتا
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# إنشاء الموديل
model = DecisionTreeClassifier()

# تدريب الموديل
model.fit(X_train, y_train)

# التوقع
predictions = model.predict(X_test)

# حساب الدقة
accuracy = accuracy_score(y_test, predictions)

print("Predictions:", predictions)
print("Accuracy:", accuracy)

# تجربة على بيانات جديدة
new_data = [[28, 70000]]
result = model.predict(new_data)

print("Prediction for new data:", result)

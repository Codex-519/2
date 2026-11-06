a=int(input("Enter a number: "))
op=input("Enter an operator (+, -, *, /): ")
b=int(input("Enter another number: "))
if op=="+":
    print("Answer :", a + b)
elif op=="-":
    print("Answer :", a - b)
elif op=="*":
    print("Answer :", a * b)
elif op=="/":
    if b != 0:
        print("Answer :", a / b)
    else:
        print("Cannot divide by zero")
else:
    print("Invalid operator")
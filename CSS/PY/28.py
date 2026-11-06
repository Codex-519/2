num=int(input("Enter a number: "))
for i in range(1, num):
    if i%2==0:
        print(f"{i} is Even")
    else:
        print(f"{i} is Odd")
import argparse
import psycopg2
from contextlib import contextmanager
from datetime import datetime
import os
import re

SESSION_FILE = 'session.txt'

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="realestate_db",
            user="postgres",
            password="1234"
        )
        yield conn
    finally:
        if conn is not None:
            conn.close()

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_card(card):
    return card.isdigit() and len(card) == 16

def is_valid_expiry(expiry):
    try:
        exp_date = datetime.strptime(expiry, "%Y-%m-%d")
        return exp_date > datetime.now()
    except Exception:
        return False

def save_session(email, role):
    with open(SESSION_FILE, 'w') as f:
        f.write(f"{email},{role}")

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            email, role = f.read().strip().split(',')
            return email, role
    return None, None

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

def login(email):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT Email FROM Renter WHERE Email = %s', (email,))
                renter_result = cur.fetchone()
                cur.execute('SELECT Email FROM Agent WHERE Email = %s', (email,))
                agent_result = cur.fetchone()
                if renter_result:
                    save_session(email, 'renter')
                    print(f"Logged in as {email} (renter)")
                elif agent_result:
                    save_session(email, 'agent')
                    print(f"Logged in as {email} (agent)")
                else:
                    print("Login failed: User not found.")
    except Exception as e:
        print(f"Error logging in: {str(e)}")

def register_user(email, name, user_type):
    if not is_valid_email(email):
        print("Invalid email format.")
        return
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM "User" WHERE Email = %s', (email,))
                if cur.fetchone():
                    print(f"Registration failed: Email {email} already exists.")
                    return
                cur.execute('''
                    INSERT INTO "User" (Email, Name)
                    VALUES (%s, %s)
                ''', (email, name))
                if user_type == 'agent':
                    cur.execute('''
                        INSERT INTO Agent (Email, Job_Title, Agency, Contact_Info)
                        VALUES (%s, %s, %s, %s)
                    ''', (email, 'Job Title', 'Agency Name', 'Contact Info'))
                elif user_type == 'renter':
                    cur.execute('''
                        INSERT INTO Renter (Email, Budget, Preferred_Location, Move_in_Date, Reward_Points)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (email, 0.0, 'Preferred Location', '2025-01-01', 0))
                conn.commit()
        print(f"""Registration successful!
              User: {name}
              Email: {email}
              Role: {user_type}
              """)
    except Exception as e:
        print(f"Error registering user: {str(e)}")

def manage_payment_info(action, card_info=None, billing_address=None, expiry="2025-01-01", cvv=None):
    session_email, role = load_session()
    if role != 'renter':
        print("Access denied: Only renters can manage payment information.")
        return

    if action in ['add', 'modify']:
        if not is_valid_card(card_info):
            print("Invalid card number. Must be 16 digits.")
            return
        if not is_valid_expiry(expiry):
            print("Invalid expiry date. Must be in YYYY-MM-DD format and in the future.")
            return
        if not (cvv and cvv.isdigit() and len(cvv) == 3):
            print("Invalid CVV. Must be 3 digits.")
            return

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if action == 'add':
                    cur.execute('SELECT 1 FROM Address WHERE Email = %s AND AddressID = %s', (session_email, billing_address))
                    if not cur.fetchone():
                        print("Billing address does not exist or does not belong to you.")
                        return
                    cur.execute('''
                        INSERT INTO CreditCard (Card_Number, CVV, Expiry_Date, Renter_Email, Billing_Address)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (Renter_Email, Card_Number) DO NOTHING;
                    ''', (card_info, cvv, expiry, session_email, billing_address))
                    print(f"""Credit card added!
                          Card Number: {card_info}
                          Billing Address ID: {billing_address}
                          Expiry: {expiry}
                          CVV: {cvv}
                          """)
                elif action == 'modify':
                    cur.execute('SELECT 1 FROM CreditCard WHERE Renter_Email = %s AND Card_Number = %s', (session_email, card_info))
                    if not cur.fetchone():
                        print("Credit card not found.")
                        return
                    cur.execute('''
                        UPDATE CreditCard
                        SET CVV = %s, Expiry_Date = %s, Billing_Address = %s
                        WHERE Renter_Email = %s AND Card_Number = %s;
                    ''', (cvv, expiry, billing_address, session_email, card_info))
                    print(f"""Credit card modified!
                          Card Number: {card_info}
                          Billing Address ID: {billing_address}
                          Expiry: {expiry}
                          CVV: {cvv}
                          """)
                elif action == 'delete':
                    cur.execute('''
                        SELECT 1 FROM Booking
                        WHERE Renter_Email = %s AND Card_Number = %s
                    ''', (session_email, card_info))
                    if cur.fetchone():
                        print("Cannot delete credit card: It is used in one or more bookings.")
                        return
                    cur.execute('''
                        DELETE FROM CreditCard
                        WHERE Renter_Email = %s AND Card_Number = %s;
                    ''', (session_email, card_info))
                    print(f"""Credit card deleted!
                          Card Number: {card_info}
                          """)
                conn.commit()
    except Exception as e:
        print(f"Error managing payment info: {str(e)}")

def manage_properties(action, property_id=None, property_info=None):
    session_email, role = load_session()
    if role != 'agent':
        print("Access denied: Only agents can manage properties.")
        return

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if action == 'add':
                    if not property_info:
                        print("Property information required.")
                        return
                    # Expecting: Street, City, State, Zip, Price, Availability, Square_Footage, Description, Type, Neighborhood, [Subtype-specific fields]
                    info = property_info.split(', ')
                    if len(info) < 10:
                        print("Property information must have at least 10 fields: Street, City, State, Zip, Price, Availability, Square_Footage, Description, Type, Neighborhood")
                        return
                    
                    # Insert into Property table
                    cur.execute('''
                        INSERT INTO Property (Street, City, State, Zip, Price, Availability, Square_Footage, Description, Type, Agent_Email, Neighborhood)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING Property_ID;
                    ''', (*info[:9], session_email, info[9]))
                    property_id = cur.fetchone()[0]

                    # Handle subtype-specific information
                    property_type = info[8].lower()
                    if property_type == 'house':
                        if len(info) < 11:
                            print("House properties require number of rooms.")
                            return
                        cur.execute('''
                            INSERT INTO House (Property_ID, Number_of_rooms)
                            VALUES (%s, %s);
                        ''', (property_id, info[10]))
                    elif property_type == 'apartment':
                        if len(info) < 12:
                            print("Apartment properties require number of rooms and floor.")
                            return
                        cur.execute('''
                            INSERT INTO Apartment (Property_ID, Number_of_rooms, Floor)
                            VALUES (%s, %s, %s);
                        ''', (property_id, info[10], info[11]))
                    elif property_type == 'vacation_home':
                        if len(info) < 12:
                            print("Vacation home properties require number of rooms and amenities.")
                            return
                        cur.execute('''
                            INSERT INTO Vacation_Home (Property_ID, Number_of_rooms, Amenities)
                            VALUES (%s, %s, %s);
                        ''', (property_id, info[10], info[11]))

                    print(f"""Property added!
                          Property ID: {property_id}
                          Street: {info[0]}
                          City: {info[1]}
                          State: {info[2]}
                          Zip: {info[3]}
                          Price: {info[4]}
                          Square Footage: {info[6]}
                          Type: {info[8]}
                          Neighborhood: {info[9]}
                          """)
                    
                    # Print subtype-specific information
                    if property_type == 'house':
                        print(f"Number of rooms: {info[10]}")
                    elif property_type == 'apartment':
                        print(f"Number of rooms: {info[10]}")
                        print(f"Floor: {info[11]}")
                    elif property_type == 'vacation_home':
                        print(f"Number of rooms: {info[10]}")
                        print(f"Amenities: {info[11]}")

                elif action == 'modify':
                    if not property_id or not property_info:
                        print("Property ID and new info required.")
                        return
                    # property_info: Price, Availability, Square_Footage, Description, Type, Neighborhood, [Subtype-specific fields]
                    fields = property_info.split(', ')
                    if len(fields) < 2:
                        print("Property info must have at least Price and Availability.")
                        return
                    price, availability = fields[0], fields[1]
                    
                    # Update Property table
                    cur.execute('''
                        UPDATE Property
                        SET Price = %s, Availability = %s
                        WHERE Agent_Email = %s AND Property_ID = %s;
                    ''', (price, availability, session_email, property_id))

                    # Update subtype-specific information if provided
                    if len(fields) > 5:  # If subtype info is provided
                        property_type = fields[4].lower()
                        if property_type == 'house' and len(fields) > 6:
                            cur.execute('''
                                UPDATE House
                                SET Number_of_rooms = %s
                                WHERE Property_ID = %s;
                            ''', (fields[6], property_id))
                        elif property_type == 'apartment' and len(fields) > 7:
                            cur.execute('''
                                UPDATE Apartment
                                SET Number_of_rooms = %s, Floor = %s
                                WHERE Property_ID = %s;
                            ''', (fields[6], fields[7], property_id))
                        elif property_type == 'vacation_home' and len(fields) > 7:
                            cur.execute('''
                                UPDATE Vacation_Home
                                SET Number_of_rooms = %s, Amenities = %s
                                WHERE Property_ID = %s;
                            ''', (fields[6], fields[7], property_id))

                    print(f"""Property modified!
                          Property ID: {property_id}
                          New Price: {price}
                          Availability: {availability}
                          """)

                elif action == 'delete':
                    if not property_id:
                        print("Property ID required.")
                        return
                    
                    # Delete from subtype table first
                    cur.execute('SELECT Type FROM Property WHERE Property_ID = %s', (property_id,))
                    property_type = cur.fetchone()[0].lower()
                    
                    if property_type == 'house':
                        cur.execute('DELETE FROM House WHERE Property_ID = %s', (property_id,))
                    elif property_type == 'apartment':
                        cur.execute('DELETE FROM Apartment WHERE Property_ID = %s', (property_id,))
                    elif property_type == 'vacation_home':
                        cur.execute('DELETE FROM Vacation_Home WHERE Property_ID = %s', (property_id,))
                    
                    # Then delete from Property table
                    cur.execute('''
                        DELETE FROM Property
                        WHERE Agent_Email = %s AND Property_ID = %s;
                    ''', (session_email, property_id))
                    print(f"""Property deleted!
                          Property ID: {property_id}
                          """)
                conn.commit()
    except Exception as e:
        print(f"Error managing properties: {str(e)}")

def search_properties(location, date, property_type=None, min_bedrooms=None, max_bedrooms=None, min_price=None, max_price=None, order_by=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = '''
                    SELECT p.Property_ID, p.Street, p.City, p.State, p.Zip, p.Price, p.Type, p.Description, 
                        COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, NULL) as Bedrooms,
                        p.Square_Footage, p.Neighborhood,
                        CASE 
                            WHEN p.Type = 'House' THEN h.Number_of_rooms::text
                            WHEN p.Type = 'Apartment' THEN a.Number_of_rooms::text || ', Floor ' || a.Floor::text
                            WHEN p.Type = 'Vacation_Home' THEN v.Number_of_rooms::text || ', ' || v.Amenities
                            ELSE NULL
                        END as Subtype_Info
                    FROM Property p
                    LEFT JOIN House h ON p.Property_ID = h.Property_ID
                    LEFT JOIN Apartment a ON p.Property_ID = a.Property_ID
                    LEFT JOIN Vacation_Home v ON p.Property_ID = v.Property_ID
                    WHERE p.City = %s AND p.Availability = TRUE
                    AND NOT EXISTS (
                        SELECT 1 FROM Booking b
                        WHERE b.Property_ID = p.Property_ID
                          AND %s BETWEEN b.Start_Date AND b.End_Date
                    )
                '''
                params = [location, date]
                if property_type:
                    query += ' AND p.Type = %s'
                    params.append(property_type)
                if min_bedrooms:
                    query += ' AND COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, 0) >= %s'
                    params.append(min_bedrooms)
                if max_bedrooms:
                    query += ' AND COALESCE(h.Number_of_rooms, a.Number_of_rooms, v.Number_of_rooms, 100) <= %s'
                    params.append(max_bedrooms)
                if min_price:
                    query += ' AND p.Price >= %s'
                    params.append(min_price)
                if max_price:
                    query += ' AND p.Price <= %s'
                    params.append(max_price)
                if order_by in ['price', 'bedrooms']:
                    query += f' ORDER BY { "p.Price" if order_by == "price" else "Bedrooms" }'
                cur.execute(query, params)
                results = cur.fetchall()
                if not results:
                    print("No properties found matching your criteria.")
                for result in results:
                    print(f"""Property Found!
                          Property ID: {result[0]}
                          Address: {result[1]}, {result[2]}, {result[3]} {result[4]}
                          Price: {result[5]}
                          Type: {result[6]}
                          Description: {result[7]}
                          Bedrooms: {result[8]}
                          Square Footage: {result[9]}
                          Neighborhood: {result[10]}
                          Subtype Info: {result[11]}
                          """)
    except Exception as e:
        print(f"Error searching properties: {str(e)}")

def book_property(property_id, start_date, end_date, payment_method):
    session_email, role = load_session()
    if role != 'renter':
        print("Access denied: Only renters can book properties.")
        return

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM CreditCard WHERE Renter_Email = %s AND Card_Number = %s', (session_email, payment_method))
                if not cur.fetchone():
                    print("Invalid payment method.")
                    return

                cur.execute('''
                    SELECT 1 FROM Booking
                    WHERE Property_ID = %s
                    AND (
                        (Start_Date <= %s AND End_Date >= %s) OR
                        (Start_Date <= %s AND End_Date >= %s) OR
                        (Start_Date >= %s AND End_Date <= %s)
                    )
                ''', (property_id, start_date, start_date, end_date, end_date, start_date, end_date))
                if cur.fetchone():
                    print("Property is not available for the selected period.")
                    return

                cur.execute('SELECT Price, Street, City, State, Zip, Type, Description FROM Property WHERE Property_ID = %s', (property_id,))
                prop = cur.fetchone()
                if not prop:
                    print("Property not found.")
                    return
                price = float(prop[0])

                days = (end_date - start_date).days
                if days <= 0:
                    print("End date must be after start date.")
                    return
                total_cost = days * price

                # Add reward points equal to the rental price
                cur.execute('''
                    UPDATE Renter
                    SET Reward_Points = Reward_Points + %s
                    WHERE Email = %s
                ''', (total_cost, session_email))

                cur.execute('''
                    INSERT INTO Booking (Property_ID, Renter_Email, Booking_Date, Card_Number, Start_Date, End_Date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (property_id, session_email, datetime.now().date(), payment_method, start_date, end_date))
                conn.commit()

                # Get updated reward points
                cur.execute('SELECT Reward_Points FROM Renter WHERE Email = %s', (session_email,))
                reward_points = cur.fetchone()[0]

                print(f"""Booking successful!
                      Property ID: {property_id}
                      Address: {prop[1]}, {prop[2]}, {prop[3]} {prop[4]}
                      Type: {prop[5]}
                      Description: {prop[6]}
                      Renter: {session_email}
                      Rental period: {start_date} to {end_date}
                      Payment method: {payment_method}
                      Total cost: ${total_cost:.2f}
                      Reward points earned: {total_cost}
                      Total reward points: {reward_points}
                      """)
    except Exception as e:
        print(f"Error booking property: {str(e)}")

def manage_bookings(action, booking_id=None):
    session_email, role = load_session()
    if role not in ['renter', 'agent']:
        print("Access denied: Only renters and agents can manage bookings.")
        return

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if action == 'view':
                    if role == 'renter':
                        cur.execute('''
                            SELECT b.Booking_ID, b.Property_ID, b.Start_Date, b.End_Date, b.Card_Number, p.Price, p.Street, p.City, p.State, p.Zip, p.Type, p.Description
                            FROM Booking b
                            JOIN Property p ON b.Property_ID = p.Property_ID
                            WHERE b.Renter_Email = %s;
                        ''', (session_email,))
                        bookings = cur.fetchall()
                        for booking in bookings:
                            start_date = booking[2]
                            end_date = booking[3]
                            if start_date is None or end_date is None:
                                print(f"""BookingID: {booking[0]}
                                      PropertyID: {booking[1]}
                                      Period: MISSING DATES
                                      Card: {booking[4]}
                                      Total: UNKNOWN
                                      """)
                                continue
                            days = (end_date - start_date).days
                            total_cost = days * float(booking[5])
                            print(f"""BookingID: {booking[0]}
                                  PropertyID: {booking[1]}
                                  Address: {booking[6]}, {booking[7]}, {booking[8]} {booking[9]}
                                  Type: {booking[10]}
                                  Description: {booking[11]}
                                  Period: {start_date} to {end_date}
                                  Card: {booking[4]}
                                  Total: ${total_cost:.2f}
                                  """)
                    elif role == 'agent':
                        cur.execute('''
                            SELECT b.Booking_ID, b.Property_ID, b.Start_Date, b.End_Date, b.Card_Number, b.Renter_Email, p.Price, p.Street, p.City, p.State, p.Zip, p.Type, p.Description
                            FROM Booking b
                            JOIN Property p ON b.Property_ID = p.Property_ID
                            WHERE p.Agent_Email = %s;
                        ''', (session_email,))
                        bookings = cur.fetchall()
                        for booking in bookings:
                            start_date = booking[2]
                            end_date = booking[3]
                            if start_date is None or end_date is None:
                                print(f"""BookingID: {booking[0]}
                                      PropertyID: {booking[1]}
                                      Period: MISSING DATES
                                      Card: {booking[4]}
                                      Renter: {booking[5]}
                                      Total: UNKNOWN
                                      """)
                                continue
                            days = (end_date - start_date).days
                            total_cost = days * float(booking[6])
                            print(f"""BookingID: {booking[0]}
                                  PropertyID: {booking[1]}
                                  Address: {booking[7]}, {booking[8]}, {booking[9]} {booking[10]}
                                  Type: {booking[11]}
                                  Description: {booking[12]}
                                  Period: {start_date} to {end_date}
                                  Card: {booking[4]}
                                  Renter: {booking[5]}
                                  Total: ${total_cost:.2f}
                                  """)
                elif action == 'cancel' and booking_id:
                    # Fetch booking details for refund message
                    cur.execute('''
                        SELECT Card_Number, Renter_Email FROM Booking
                        WHERE Booking_ID = %s
                    ''', (booking_id,))
                    booking = cur.fetchone()
                    if not booking:
                        print("Booking not found.")
                        return
                    card, renter = booking
                    if role == 'renter':
                        cur.execute('''
                            DELETE FROM Booking
                            WHERE Booking_ID = %s AND Renter_Email = %s;
                        ''', (booking_id, session_email))
                        print(f"""Booking canceled!
                              Booking ID: {booking_id}
                              Refund issued to card: {card}
                              """)
                    elif role == 'agent':
                        cur.execute('''
                            DELETE FROM Booking
                            WHERE Booking_ID = %s AND EXISTS (
                                SELECT 1 FROM Property p
                                WHERE p.Property_ID = Booking.Property_ID AND p.Agent_Email = %s
                            );
                        ''', (booking_id, session_email))
                        print(f"""Booking canceled by agent!
                              Booking ID: {booking_id}
                              Refund issued to renter {renter} on card: {card}
                              """)
                    conn.commit()
    except Exception as e:
        print(f"Error managing bookings: {str(e)}")

def add_address(address_info):
    session_email, role = load_session()
    if role != 'renter':
        print("Access denied: Only renters can manage addresses.")
        return

    try:
        street, city, state, zip_code, primary_address = address_info.split(', ')
        primary_address = primary_address.upper() == 'TRUE'
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if primary_address:
                    cur.execute('UPDATE Address SET Primary_Address = FALSE WHERE Email = %s', (session_email,))
                cur.execute('''
                    INSERT INTO Address (Street, City, State, Zip, Email, Primary_Address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING AddressID
                ''', (street, city, state, zip_code, session_email, primary_address))
                new_address_id = cur.fetchone()[0]
                conn.commit()
        print(f"""Address added!
              AddressID: {new_address_id}
              Street: {street}
              City: {city}
              State: {state}
              Zip: {zip_code}
              Primary: {primary_address}
              """)
    except Exception as e:
        print(f"Error adding address: {str(e)}")

def modify_address(address_id, address_info):
    session_email, role = load_session()
    if role != 'renter':
        print("Access denied: Only renters can manage addresses.")
        return

    try:
        street, city, state, zip_code, primary_address = address_info.split(', ')
        primary_address = primary_address.upper() == 'TRUE'
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM Address WHERE Email = %s AND AddressID = %s', (session_email, address_id))
                if not cur.fetchone():
                    print(f"Error: Address {address_id} not found or not owned by you.")
                    return
                if primary_address:
                    cur.execute('UPDATE Address SET Primary_Address = FALSE WHERE Email = %s', (session_email,))
                cur.execute('''
                    UPDATE Address
                    SET Street = %s, City = %s, State = %s, Zip = %s, Primary_Address = %s
                    WHERE Email = %s AND AddressID = %s
                ''', (street, city, state, zip_code, primary_address, session_email, address_id))
                conn.commit()
        print(f"""Address modified!
              AddressID: {address_id}
              Street: {street}
              City: {city}
              State: {state}
              Zip: {zip_code}
              Primary: {primary_address}
              """)
    except Exception as e:
        print(f"Error modifying address: {str(e)}")

def delete_address(address_id):
    session_email, role = load_session()
    if role != 'renter':
        print("Access denied: Only renters can manage addresses.")
        return

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT Street, City, State, Zip, Primary_Address FROM Address WHERE Email = %s AND AddressID = %s', (session_email, address_id))
                address = cur.fetchone()
                if not address:
                    print(f"Error: Address {address_id} not found or not owned by you.")
                    return
                cur.execute('''
                    SELECT 1 FROM CreditCard
                    WHERE Billing_Address = %s AND Renter_Email = %s
                ''', (address_id, session_email))
                if cur.fetchone():
                    print("Cannot delete address: It is used as a billing address for a credit card.")
                    return
                cur.execute('''
                    DELETE FROM Address
                    WHERE Email = %s AND AddressID = %s
                ''', (session_email, address_id))
                conn.commit()
        print(f"""Address deleted!
              AddressID: {address_id}
              Street: {address[0]}
              City: {address[1]}
              State: {address[2]}
              Zip: {address[3]}
              Primary: {address[4]}
              """)
    except Exception as e:
        print(f"Error deleting address: {str(e)}")

def view_addresses():
    session_email, role = load_session()
    if not session_email:
        print("Not logged in.")
        return
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT AddressID, Street, City, State, Zip, Primary_Address FROM Address WHERE Email = %s', (session_email,))
                addresses = cur.fetchall()
                if addresses:
                    for address in addresses:
                        print(f"""AddressID: {address[0]}
                              Street: {address[1]}
                              City: {address[2]}
                              State: {address[3]}
                              Zip: {address[4]}
                              Primary: {address[5]}
                              """)
                else:
                    print("No addresses found for this user.")
    except Exception as e:
        print(f"Error viewing addresses: {str(e)}")

def view_reward_points():
    session_email, role = load_session()
    if role != 'renter':
        print("Access denied: Only renters can view reward points.")
        return

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT Reward_Points FROM Renter WHERE Email = %s', (session_email,))
                result = cur.fetchone()
                if result:
                    print(f"""Reward Points Information:
                          Email: {session_email}
                          Total Reward Points: {result[0]}
                          """)
                else:
                    print("No reward points information found.")
    except Exception as e:
        print(f"Error viewing reward points: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Real Estate Management CLI")
    subparsers = parser.add_subparsers(dest='command')

    # Login
    login_parser = subparsers.add_parser('login', help='Login as a user')
    login_parser.add_argument('email', type=str, help='Email of the user')

    # Register user
    register_parser = subparsers.add_parser('register', help='Register a new user')
    register_parser.add_argument('email', type=str, help='Email of the user')
    register_parser.add_argument('name', type=str, help='Name of the user')
    register_parser.add_argument('user_type', type=str, choices=['agent', 'renter'], help='Type of user')

    # Manage payment info
    payment_parser = subparsers.add_parser('manage_payment', help='Manage payment and address information')
    payment_parser.add_argument('action', type=str, choices=['add', 'modify', 'delete'], help='Action to perform')
    payment_parser.add_argument('--card_info', type=str, help='Credit card information')
    payment_parser.add_argument('--billing_address', type=int, help='Billing address ID')
    payment_parser.add_argument('--expiry', type=str, default="2025-01-01", help='Expiry date (YYYY-MM-DD)')
    payment_parser.add_argument('--cvv', type=str, help='CVV (3 digits)')

    # Manage properties
    property_parser = subparsers.add_parser('manage_properties', help='Manage properties')
    property_parser.add_argument('action', type=str, choices=['add', 'modify', 'delete'], help='Action to perform')
    property_parser.add_argument('--property_id', type=int, help='ID of the property (for modify/delete)')
    property_parser.add_argument('--property_info', type=str, help='Property information')

    # Search properties
    search_parser = subparsers.add_parser('search_properties', help='Search for properties')
    search_parser.add_argument('location', type=str, help='Location to search')
    search_parser.add_argument('date', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), help='Date for availability')
    search_parser.add_argument('--property_type', type=str, help='Property type')
    search_parser.add_argument('--min_bedrooms', type=int, help='Minimum bedrooms')
    search_parser.add_argument('--max_bedrooms', type=int, help='Maximum bedrooms')
    search_parser.add_argument('--min_price', type=float, help='Minimum price')
    search_parser.add_argument('--max_price', type=float, help='Maximum price')
    search_parser.add_argument('--order_by', type=str, choices=['price', 'bedrooms'], help='Order by')

    # Book property
    book_parser = subparsers.add_parser('book_property', help='Book a property')
    book_parser.add_argument('property_id', type=int, help='ID of the property')
    book_parser.add_argument('start_date', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), help='Start date of rental')
    book_parser.add_argument('end_date', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), help='End date of rental')
    book_parser.add_argument('payment_method', type=str, help='Payment method to use')

    # Manage bookings
    booking_parser = subparsers.add_parser('manage_bookings', help='Manage bookings')
    booking_parser.add_argument('action', type=str, choices=['view', 'cancel'], help='Action to perform')
    booking_parser.add_argument('--booking_id', type=int, help='ID of the booking to manage')

    # Manage addresses
    address_parser = subparsers.add_parser('manage_address', help='Manage addresses')
    address_parser.add_argument('action', type=str, choices=['add', 'view', 'modify', 'delete'], help='Action to perform')
    address_parser.add_argument('--address_info', type=str, help='Address information')
    address_parser.add_argument('--address_id', type=int, help='ID of the address to modify or delete')

    # View reward points
    reward_parser = subparsers.add_parser('view_rewards', help='View reward points')

    args = parser.parse_args()

    if args.command == 'login':
        login(args.email)
    elif args.command == 'register':
        register_user(args.email, args.name, args.user_type)
    elif args.command == 'manage_payment':
        manage_payment_info(args.action, args.card_info, args.billing_address, args.expiry, args.cvv)
    elif args.command == 'manage_properties':
        manage_properties(args.action, args.property_id, args.property_info)
    elif args.command == 'search_properties':
        search_properties(args.location, args.date, args.property_type, args.min_bedrooms, args.max_bedrooms, args.min_price, args.max_price, args.order_by)
    elif args.command == 'book_property':
        book_property(args.property_id, args.start_date, args.end_date, args.payment_method)
    elif args.command == 'manage_bookings':
        manage_bookings(args.action, args.booking_id)
    elif args.command == 'manage_address':
        if args.action == 'add':
            add_address(args.address_info)
        elif args.action == 'view':
            view_addresses()
        elif args.action == 'modify':
            modify_address(args.address_id, args.address_info)
        elif args.action == 'delete':
            delete_address(args.address_id)
    elif args.command == 'view_rewards':
        view_reward_points()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()


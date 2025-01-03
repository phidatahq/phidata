from cookbook.examples.customer_support.setup import setup_database
from phi.model.openai.chat import OpenAIChat
from phi.tools.postgres import PostgresTools
from phi.workflow.workflow import Workflow
from phi.agent.agent import Agent


class CustomerSupportWorkflow(Workflow):
    db_url: str = "postgresql+psycopg://ai:ai@localhost:5532/ai"

    database_agent: Agent = Agent(
        name="Database Agent",
        description="You are an agent that can query the database",
        instructions=[
            "You are an agent that can query the database",
            "You have access to the database and tables users, products, orders, order_items",
            "You can use the following tools to query the database: PostgresTools",
            "Database schema:",
            "users table:",
            "- id (Integer, primary key)",
            "- name (String)",
            "- email (String)",
            "- orders (relationship to Order)",
            "products table:",
            "- id (Integer, primary key)",
            "- name (String)",
            "- description (String)",
            "- price (Float)",
            "- stock_quantity (Integer)",
            "- orders (relationship to OrderItem)",
            "orders table:",
            "- id (Integer, primary key)",
            "- user_id (Integer, foreign key to users.id)",
            "- order_date (DateTime)",
            "- status (Enum: ordered, dispatched, returned, completed, cancelled)",
            "- items (relationship to OrderItem)",
            "- user (relationship to User)",
            "order_items table:",
            "- id (Integer, primary key)",
            "- order_id (Integer, foreign key to orders.id)",
            "- product_id (Integer, foreign key to products.id)",
            "- quantity (Integer)",
            "- order (relationship to Order)",
            "- product (relationship to Product)",
        ],
        model=OpenAIChat(model="gpt-4o"),
        tools=[PostgresTools(db_name="ai", user="ai", password="ai", host="localhost", port=5532)],
    )

    general_agent: Agent = Agent(
        name="General Agent",
        description="You are a e-commerce customer support agent that can help with general queries",
        instructions=[
            "You are a e-commerce customer support agent that can help with general queries",
            "Your job is to help the customer with their general queries where you don't have to make any database queries",
        ],
        model=OpenAIChat(model="gpt-4o"),
    )

    def __init__(self):
        super().__init__()
        setup_database()

    @Workflow.register(description="Order a product for a user")
    def order_product(self, user_email: str, product_id: int) -> str:
        response = self.database_agent.run(f"Order a product for user {user_email} with product id {product_id}")
        return str(response.content)

    @Workflow.register(description="Get the product id of an order")
    def get_product_id(self, product_name: str) -> str:
        response = self.database_agent.run(f"Get the product id of product {product_name}")
        return str(response.content)

    @Workflow.register(description="Get order status")
    def get_order_status(self, order_id: int) -> str:
        response = self.database_agent.run(f"Get the status of order {order_id}")
        return str(response.content)

    @Workflow.register(description="Get all orders for a user")
    def get_all_orders(self, user_email: str) -> str:
        response = self.database_agent.run(f"Get all orders for user {user_email}")
        return str(response.content)

    @Workflow.register(description="Get the latest order for a user")
    def get_latest_order(self, user_email: str) -> str:
        response = self.database_agent.run(f"Get the latest order for user {user_email}")
        return str(response.content)

    @Workflow.register(description="Return an order")
    def return_order(self, order_id: int, user_email: str) -> str:
        response = self.database_agent.run(
            f"Return order {order_id} for user {user_email} if the order status is COMPLETED else cancel the order"
        )
        return str(response.content)

    @Workflow.register(description="Cancel an order")
    def cancel_order(self, order_id: int, user_email: str) -> str:
        response = self.database_agent.run(
            f"Cancel order {order_id} for user {user_email} if the order status is ORDERED or DISPATCHED"
        )
        return str(response.content)

    @Workflow.register(description="Handle a general query")
    def handle_general_query(self, query: str) -> str:
        response = self.general_agent.run(f"Handle the general query: {query}")
        return str(response.content)

    @Workflow.register(description="Get the details of a product")
    def get_product_details(self, product_id: int) -> str:
        response = self.database_agent.run(f"Get the details of product {product_id}")
        return str(response.content)

    @Workflow.register(description="Get the details of an order")
    def get_order_details(self, order_id: int) -> str:
        response = self.database_agent.run(f"Get the details of order {order_id}")
        return str(response.content)


agent = Agent(
    name="Customer Support Agent",
    description="You are a customer support agent that can help with general queries and order products for users",
    instructions=[
        "You are a customer support agent that can help with general queries and order products for users",
        "You have access to the database and tables users, products, orders, order_items",
        "You can use the following tools to order products: PostgresTools",
    ],
    model=OpenAIChat(model="gpt-4o"),
    workflows=[CustomerSupportWorkflow()],
)

agent.print_response("Order a Headphone and Laptop for john@example.com")

agent.print_response("Can you help me with status of my latest order for john@example.com?")

agent.print_response("What is your return policy?")

agent.print_response("I want to return my latest order for john@example.com")

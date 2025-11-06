//导入路由
import { Routes, Route } from "react-router-dom"
import Layout from "./pages/Layout"
import Newpage from "./pages/Newpage"
import Todo from "./pages/Todo"
import Login from "./pages/Login"
import Register from "./pages/Register"
import Search from './pages/Search'

export default function App() {
    return (<>
        <Routes>
            {/*设置默认路由*/}
            <Route path='/' element={<Layout></Layout>}>
                {/**子集路由嵌套 */}
                <Route index element={<Newpage></Newpage>}></Route>
                <Route path="/" element={<Newpage />} />
                {/**设置id跳转 */}
                <Route path="/todo/:id" element={<Todo></Todo>}></Route>
                <Route path="/search" element={<Search></Search>}></Route>
            </Route>

            {/**登录页面 */}
            <Route path="/login" element={<Login />} />
            {/**注册页面 */}
            <Route path="/register" element={<Register />} />
        </Routes>
    </>)
}
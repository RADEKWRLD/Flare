import { configureStore } from "@reduxjs/toolkit";
import todosReducer from '../store/todosSlice.js'
import authReducer from '../store/authSlice.js'

const store = configureStore({
    reducer:{
        auth: authReducer,
        todos:todosReducer
    }
})

export default store
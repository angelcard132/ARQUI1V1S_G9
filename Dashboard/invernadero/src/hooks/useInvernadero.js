import { useContext } from 'react'
import { Ctx } from '../context/InvernaderoContext'

export const useInvernadero = () => useContext(Ctx)